import pandas as pd

pd.options.mode.chained_assignment = None
from users.models import User
from pandas import json_normalize

from retweet_picker.bulk_upsert import bulk_upsert_retweet_contestants
from retweet_picker.models import ContestUserAccounts, ContestUserParticipation, TwitterGiveawayID, GiveawayResults
from retweet_picker.twitter_interact import GridGiveawayTweetRetriever


# Prep to just retrieve tweets and upload in chunks of 1000 instead of holding all in memory

class ProcessRetrievedTweets(GridGiveawayTweetRetriever):
    def __init__(self, user_id=None, tweet_url=None, process_tweets=True):
        super(ProcessRetrievedTweets, self).__init__(tweet_url)
        try:
            self.process_tweets = process_tweets
            # self.user_ids = set(tweets_df['user.id_str']) #User Twitter IDs
            self.user_ids = None
            self.participants = None
            self.user_id = user_id
            self.max_tweets = 10000000
            self.gwid = 0
        except Exception as e:
            print(f'[!] ERROR: Could not initialize TweetRetriever. Reason: {e}')

    def filter_and_rename_fields(self):
        # Assumes all_tweets has tweets retrieved
        # print("=== photo_img :", self.all_tweets[0].user.profile_image_url)
        tweets = json_normalize(self.all_tweets)
        filter_df = tweets[['user.id_str', 'user.name', 'user.screen_name', 'user.location', 'user.profile_image_url',
                            'user.created_at']]
        filter_df.columns = ['user_id', 'user_handle', 'user_screen_name', 'location', 'profile_img', 'account_created']
        filter_df.loc[:, 'account_created'] = pd.to_datetime(filter_df['account_created'])

        temp_df = filter_df[['user_id', 'user_handle', 'user_screen_name', 'location']]
        temp_df.replace(r'\s+|\\n|\\|/|,', ' ', regex=True, inplace=True)

        # Merge sanitized values back to original df
        filter_df[['user_id',
                   'user_handle',
                   'user_screen_name',
                   'location']] = temp_df[temp_df.columns]

        filter_df.drop_duplicates('user_id', inplace=True)
        return filter_df

    def get_social_accounts_by_twitter_id(self):
        """ Build dict of existing users used for bulk update"""
        return {contestant.user_id: contestant for contestant in
                ContestUserAccounts.objects.filter(user_id__in=self.user_ids)}

    def retrieve_filter_tweets(self):
        """Responsible for building data and creating or uploading to database"""
        if self.process_tweets:
            self.get_all_tweets()  # creates self.all_tweets
            if len(self.all_tweets) > 0:
                print("=== all_tweets len: ", len(self.all_tweets))
                filtered_tweets = self.filter_and_rename_fields()
                return filtered_tweets
            else:
                return []

    def build_record_objs(self, df):
        record_objs = []
        try:
            df.apply(lambda row:
                     record_objs.append(
                         ContestUserAccounts(
                             user_id=row['user_id'],
                             user_handle=row['user_handle'],
                             user_screen_name=row['user_screen_name'],
                             location=row['location'],
                             profile_img=row['profile_img'],
                             account_created=row['account_created'])
                     ), axis=1)
        except Exception as e:
            print(f'Could not add record obj. Reason {e}')
        return record_objs

    def associate_user_participation_with_contest(self):
        user_id = 7
        # TODO Uncomment for production
        # if self.request.user:
        #     user_id = self.request.user.id
        user = User.objects.get(id=self.user_id)
        # Create contest object
        twitter_giveaway, created = TwitterGiveawayID.objects.get_or_create(tweet_url=self.tweet_url,
                                                                            defaults=dict(owner=user))
        # Filter by participants in ContestUserAccounts for dataframe to get objects
        participants = ContestUserAccounts.objects.filter(user_id__in=[x.user_id for x in self.participants])
        giveaway_results, created = GiveawayResults.objects.get_or_create(giveaway_id=twitter_giveaway)
        giveaway_results.participants = len(participants)
        # Create m2m mapping
        contest, created = ContestUserParticipation.objects.get_or_create(contest=twitter_giveaway,
                                                                          user_id=self.user_id)
        contest.save()
        contest.contestants.add(*participants)

    def run_pipeline(self):
        res = {'success': True, 'msg': ''}
        # Get all tweets and clean DF
        print('Retrieving and filtering tweets')
        contest_df = self.retrieve_filter_tweets()
        if len(self.all_tweets) == 0:
            res['success'] = False
            res['msg'] = 'No tweets found'
            return res
        # Build a list of objects for bulk insert
        print('Building participants')
        self.participants = self.build_record_objs(contest_df)
        # Insert all objects into database for users
        try:
            print('Inserting Participants')
            bulk_upsert_retweet_contestants(self.participants)
            print('Successfully uploaded {member_count} user records'.format(member_count=len(self.participants)))
            print('Building User Mapping To Contests')
            self.associate_user_participation_with_contest()
            print('Users Associated')
        except Exception as e:
            print('users could not be added to db for this contest')
            print(f'Reason: {e}')
            res['success'] = False
            res['msg'] = 'users could not be added to db for this contest'
        return res
