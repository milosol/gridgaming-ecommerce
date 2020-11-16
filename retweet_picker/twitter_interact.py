# Prep to just retrieve tweets and upload in chunks of 1000 instead of holding all in memory
import tweepy
from decouple import config
from retweet_picker.utils import id_from_url
import urllib
from .models import GiveawayWinners

import re

TWITTER_CONSUMER_KEY = config('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = config('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_TOKEN = config('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = config('TWITTER_ACCESS_SECRET')


class TwitterBase(object):
    """ Base class for auth and returns API object"""

    def __init__(self,
                 wait_on_rate_limit=True
                 ):
        self.auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        self.auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        self.api = tweepy.API(self.auth,
                              wait_on_rate_limit=wait_on_rate_limit,
                              wait_on_rate_limit_notify=True)


class TwitterInteract(TwitterBase):
    def __init__(self):
        super().__init__()

    def send_user_message(self, username, message):
        if username:
            try:
                user = self.api.get_user(username).id
                self.api.send_direct_message(user, message)
                print(F'[+] Sent message to {username}: {message}')
            except Exception as e:
                print(F'[!] Could not send message. Reason: {e}')


class GridGiveawayTweetRetriever(TwitterInteract):

    def __init__(self,
                 tweet_url=None,
                 verbose=True,
                 tweet_ratio=1,
                 wait_on_rate_limit=False,
                 winner_count=1  # How many winners
                 ):
        super().__init__()
        self.user = None
        self.tweet_id = None
        self.tweet = None
        self.users = None
        self.all_tweets = []
        self.verbose = verbose
        self.tweet_ratio = tweet_ratio
        self.final_df = None
        self.tweet_url = tweet_url

        if tweet_url:
            try:
                self.tweet_id = id_from_url(tweet_url)
            except Exception as e:
                print(F'Could not process URL: {e}')

        if self.tweet_id:
            self.tweet = self.get_tweet_text_by_id(int(self.tweet_id))
            self.author = self.tweet.author.screen_name

    def get_tweet_text_by_id(self, tweet_id=None):
        if tweet_id:
            return self.api.get_status(tweet_id, tweet_mode='extended')

    def get_all_tweets(self, max_id=-1, max_tweets=10000000, write_file=False):
        sinceId = None
        max_id = max_id
        # //however many you want to limit your collection to.  how much storage space do you have?
        maxTweets = self.max_tweets
        # maxTweets = 10000000
        # Remove last element in tweet to account for URLs
        # Take 70% of the tweet to reduce length
        split = int(self.tweet_ratio * len(self.tweet.full_text.split()))
        tweet_text = ' '.join(self.tweet.full_text.split()[:split])
        # encoded_tweet_text = urllib.parse.quote_plus(tweet_text)
        searchQuery = 'RT @{author} '.format(author=self.author) + tweet_text.replace('-',' ')
        replace_urls = re.sub('http://\S+|https://\S+', '', searchQuery)
        searchQuery = replace_urls
        #searchQuery = replace_urls[:229]  #limit to 229 characters total no matter what the ratio is for free API
        tweetCount = 0
        tweetsPerQry = 100
        #print('--search query--')
        #print(searchQuery)
        #print('--end searchquery--')
        print('[+] Retrieving all contest tweets for TWEET ID: {tweet_id}\n Tweet text: {text}'.format(
            tweet_id=self.tweet.id,
            text=self.tweet.full_text))
        
        # printing the screen names of the retweeters 
        print("[*] Downloading max {0} tweets".format(maxTweets))
        while tweetCount < maxTweets:
            try:
                if (max_id <= 0):
                    if (not sinceId):
                        new_tweets = self.api.search(q=searchQuery, count=tweetsPerQry, )
                    else:
                        new_tweets = self.api.search(q=searchQuery, count=tweetsPerQry,
                                                     since_id=sinceId)
                else:
                    if not sinceId:
                        new_tweets = self.api.search(q=searchQuery, count=tweetsPerQry,
                                                     max_id=str(max_id - 1))
                    else:
                        new_tweets = self.api.search(q=searchQuery, count=tweetsPerQry,
                                                     max_id=str(max_id - 1),
                                                     since_id=sinceId)
                if not new_tweets:
                    print('')
                    print("[!] No more tweets found")
                    break
                for tweet in new_tweets:
                    self.all_tweets.append(tweet._json)
                tweetCount += len(new_tweets)
                GiveawayWinners.objects.filter(id=self.gwid).update(loaded_count=tweetCount)
                print("[*] Downloaded {0} tweets".format(tweetCount), end='\r', flush=True)
                max_id = new_tweets[-1].id
            except tweepy.TweepError as e:
                # Just exit if any error
                print("[!!] Error : " + str(e))
                break
        return self.all_tweets
