import datetime

import pandas as pd
# TODO Replace with datetime soon
import pytz
import tweepy

from retweet_picker.twitter_interact import TwitterInteract


def p2f(x):
    return float(x.strip('%'))


class BotCheck(TwitterInteract):

    def __init__(self, username=None):
        super(BotCheck, self).__init__()
        self.username = username
        self.user_obj = self.get_user_obj()
        self.user_analysis = {}
        self.build_profile()

    """ Class to observe and predict bots"""
    features = ['creation_date', 'timeline_analysis', 'default_picture', 'name_entropy', '']

    def get_user_obj(self):
        return self.api.get_user(self.username)._json

    def get_days_old(self):
        user_created_at = self.user_obj.get('created_at')
        days_old = pytz.utc.localize(datetime.datetime.now()) - pd.to_datetime(user_created_at)
        return days_old.days

    def get_follower_count(self):
        return self.user_obj.get('followers_count')

    def get_favorites_count(self):
        return self.user_obj.get('favourites_count')

    def get_friends_count(self):
        return self.user_obj.get('friends_count')

    def get_tweet_count(self):
        return self.user_obj.get('statuses_count')

    def get_default_profile_status(self):
        """ When true, indicates that the user has not uploaded their own profile image and a default image is used instead."""
        return self.user_obj.get('default_profile')

    def get_default_profile_image(self):
        """ Returns bool if user is using default profile image"""
        return self.user_obj.get('default_profile_image')

    def get_profile_use_background_image(self):
        """ Bots usually don't have these """
        return self.user_obj.get('profile_use_background_image')

    def get_tweets_per_day(self):
        return self.user_analysis['tweet_count'] / self.user_analysis['days_old']

    def get_protected_status(self):
        """
        Whether or not the account is in protected status. Cannot see tweets if in protected mode.
        :return:
        """
        return self.user_obj.get('protected')

    def get_suspended_status(self):
        """
        Returns whether or not account is suspended - Obviously can't see tweets if account is suspended.
        :return:
        """
        return self.user_obj.get('suspended')

    def giveaway_ratio(self):
        tweet_count = []
        keywords = ['giveaway', 'give', 'cash', 'winner', 'follow', 'following', '$']
        for status in tweepy.Cursor(self.api.user_timeline, screen_name=f'@{self.username}',
                                    include_rts=True, tweet_mode="extended", count=100).items(500):
            tweet_count.append(status)
        counter = 0
        for tweet in tweet_count:
            for word in tweet.full_text.split(' '):
                if word in keywords:
                    counter += 1
                    # print(f'Mentioned Giveaway: {tweet.full_text}')
            # print(tweet.full_text)
        keyword_percent = "%.2f%%" % (counter / int(len(tweet_count)))
        # print(f'Giveaway Mention Ratio: {counter}/{len(tweet_count)} were in the keywords. \nGiveaway Ratio: {keyword_percent}')
        return keyword_percent

    def build_profile(self):
        self.user_analysis['days_old'] = self.get_days_old()
        self.user_analysis['follower_count'] = self.get_follower_count()
        self.user_analysis['tweet_count'] = self.get_tweet_count()
        self.user_analysis['favorites'] = self.get_favorites_count()
        self.user_analysis['following'] = self.get_friends_count()
        self.user_analysis['default_profile_status'] = self.get_default_profile_status()
        self.user_analysis['default_profile_image'] = self.get_default_profile_image()
        self.user_analysis['unique_background'] = self.get_profile_use_background_image()
        self.user_analysis['giveaway_timeline_analysis'] = p2f(self.giveaway_ratio())
        self.user_analysis['suspended'] = self.get_suspended_status()
        self.user_analysis['protected'] = self.get_protected_status()
        self.user_analysis['tweets_per_day'] = self.get_tweets_per_day()
        return self.user_analysis

    def bot_prediction(self):
        # TODO make days old and timeline analysis configurable
        bot = False
        if self.user_analysis['days_old'] < 60:
            bot = True

        if self.user_analysis['giveaway_timeline_analysis'] > .80:
            bot = True
        # if self.user_analysis['follower_count'] < 1000:
        #    bot = True
        return bot


class ProfileGrade:
    """
    Account Age


    """
