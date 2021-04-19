# Prep to just retrieve tweets and upload in chunks of 1000 instead of holding all in memory
from requests_oauthlib import OAuth1Session
import requests
import json
import tweepy
from decouple import config
from retweet_picker.utils import id_from_url
import urllib
from .models import GiveawayWinners

import re

TWITTER_CONSUMER_KEY = [config('TWITTER_CONSUMER_KEY'), config('PROFILE_ANALYZER_TWITTER_CONSUMER_KEY')]
TWITTER_CONSUMER_SECRET = [config('TWITTER_CONSUMER_SECRET'), config('PROFILE_ANALYZER_TWITTER_CONSUMER_SECRET')]
TWITTER_ACCESS_TOKEN = [config('TWITTER_ACCESS_TOKEN'), config('PROFILE_ANALYZER_TWITTER_ACCESS_TOKEN')]
TWITTER_ACCESS_SECRET = [config('TWITTER_ACCESS_SECRET'), config('PROFILE_ANALYZER_TWITTER_ACCESS_SECRET')]


class TwitterBase(object):
    """ Base class for auth and returns API object"""

    def __init__(self,
                 wait_on_rate_limit=True, api_index=0
                 ):
        print("========== api_index", api_index)
        self.auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY[api_index], TWITTER_CONSUMER_SECRET[api_index])
        self.auth.set_access_token(TWITTER_ACCESS_TOKEN[api_index], TWITTER_ACCESS_SECRET[api_index])
        self.api = tweepy.API(self.auth,
                              wait_on_rate_limit=wait_on_rate_limit,
                              wait_on_rate_limit_notify=True)


class TwitterInteract(TwitterBase):
    def __init__(self, api_index=0):
        super().__init__(api_index=api_index)

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
                 winner_count=1,  # How many winners
                 api_index=0):
        super().__init__(api_index)
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
        #tweet_text = ' '.join(self.tweet.full_text.split()[:split])
        # encoded_tweet_text = urllib.parse.quote_plus(tweet_text)
        tweet_text = ' '.join(self.tweet.full_text.split()[:split]).replace('-',' ')
        searchQuery = 'RT @{author} '.format(author=self.author) + tweet_text
        replace_urls = re.sub('http://\S+|https://\S+', '', searchQuery)
        searchQuery = replace_urls
        #searchQuery = replace_urls[:229]  #limit to 229 characters total no matter what the ratio is for free API
        tweetCount = 0
        tweetsPerQry = 100
        print(searchQuery)
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
                    if tweet.is_quote_status == 'True':
                        print(tweet.id, " : quoted tweet")
                        
                tweetCount += len(new_tweets)
                GiveawayWinners.objects.filter(id=self.gwid).update(loaded_count=tweetCount)
                print("[*] Downloaded {0} tweets".format(tweetCount), end='\r', flush=True)
                max_id = new_tweets[-1].id
            except tweepy.TweepError as e:
                # Just exit if any error
                print("[!!] Error : " + str(e))
                break
        return self.all_tweets

    def get_all_tweets_v2(self, max_id=-1, max_tweets=10000000, write_file=False):
        sinceId = None
        max_id = max_id 
        maxTweets = self.max_tweets
        split = int(self.tweet_ratio * len(self.tweet.full_text.split()))
        tweet_text = ' '.join(self.tweet.full_text.split()[:split]).replace('-',' ')
        searchQuery = 'RT @{author} '.format(author=self.author) + tweet_text
        searchQuery_quote = 'quoted_tweet_id:{tweet_id} '.format(tweet_id=self.tweet.id)
        replace_urls = re.sub('http://\S+|https://\S+', '', searchQuery)
        searchQuery = replace_urls
        tweetCount = 0
        tweetsPerQry = 100
        
        print('----- search query -----')
        print(searchQuery)
        print('-----end searchquery-----')
        
        print('[+] Retrieving all contest tweets for TWEET ID: {tweet_id}\n Tweet text: {text}'.format(
            tweet_id=self.tweet.id,
            text=self.tweet.full_text))
        
        print("[*] Downloading max {0} tweets".format(maxTweets))
        try:
            new_tweets = self.api.search(q=searchQuery_quote, count=tweetsPerQry)
            for tweet in new_tweets:
                self.all_tweets.append(tweet._json)
                print(tweet.id, " : quoted tweet")
            tweetCount += len(new_tweets)
            GiveawayWinners.objects.filter(id=self.gwid).update(loaded_count=tweetCount)
            print("[*] Downloaded {0} tweets".format(tweetCount), end='\r', flush=True)
        except Exception as e:
            print(" == error while searching quoted tweets == ")
            print(e)
            
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
'''
    def custom_search(self, query='', count=100, max_id='-1', since_id=0):
        print("=== here is custom serach")
        bearer_token = config("TWITTER_BEARER_TOKEN")
        url = self.create_url()
        headers = {"Authorization": "Bearer {}".format(bearer_token)}
        json_response = self.connect_to_endpoint(url, headers)
        print(json.dumps(json_response, indent=4, sort_keys=True))
        return json_response
        
        fields = "created_at,description"
        params = {"usernames": "TwitterDev,TwitterAPI", "user.fields": fields}

        # Get request token
        request_token_url = "https://api.twitter.com/oauth/request_token"
        oauth = OAuth1Session(TWITTER_CONSUMER_KEY, client_secret=TWITTER_CONSUMER_SECRET)

        try:
            fetch_response = oauth.fetch_request_token(request_token_url)
        except ValueError:
            print(
                "There may have been an issue with the consumer_key or consumer_secret you entered."
            )

        resource_owner_key = fetch_response.get("oauth_token")
        resource_owner_secret = fetch_response.get("oauth_token_secret")
        print("Got OAuth token: %s" % resource_owner_key)

        # # Get authorization
        base_authorization_url = "https://api.twitter.com/oauth/authorize"
        authorization_url = oauth.authorization_url(base_authorization_url)
        print("Please go here and authorize: %s" % authorization_url)
        verifier = input("Paste the PIN here: ")

        # Get the access token
        access_token_url = "https://api.twitter.com/oauth/access_token"
        oauth = OAuth1Session(
            TWITTER_CONSUMER_KEY,
            client_secret=TWITTER_CONSUMER_SECRET,
            resource_owner_key=resource_owner_key,
            resource_owner_secret=resource_owner_secret,
            verifier=verifier,
        )
        oauth_tokens = oauth.fetch_access_token(access_token_url)

        access_token = oauth_tokens["oauth_token"]
        access_token_secret = oauth_tokens["oauth_token_secret"]

        # Make the request
        oauth = OAuth1Session(
            TWITTER_CONSUMER_KEY,
            client_secret=TWITTER_CONSUMER_SECRET,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
  
        oauth = OAuth1Session(
            TWITTER_CONSUMER_KEY,
            client_secret=TWITTER_CONSUMER_SECRET,
            resource_owner_key=TWITTER_ACCESS_TOKEN,
            resource_owner_secret=TWITTER_ACCESS_SECRET,
        )
        print("=== after oatuh")
        params = {
            'query': '',
            # until_id: max_id,
            # since_id: since_id,
            # 'count': count
        }
        print(" ==== before get")
        # response = oauth.get(
        #     "https://api.twitter.com/2/tweets/search/recent", params=params
        # )
        response = oauth.get(
            "https://api.twitter.com/1.1/search/tweets.json", params=params
        )
        print("=== resp : ", response)
        print("=== resp status code : ", response.status_code)
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(response.status_code, response.text)
            )
        
        print("Response code: {}".format(response.status_code))
        json_response = response.json()
        print("=== resp json : ", json_response)
        return json_response
        

    def create_url(self):
        query = "from:GridGaming -is:retweet"
        # Tweet fields are adjustable.
        # Options include:
        # attachments, author_id, context_annotations,
        # conversation_id, created_at, entities, geo, id,
        # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
        # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
        # source, text, and withheld
        tweet_fields = "tweet.fields=author_id"
        url = "https://api.twitter.com/2/tweets/search/recent?query={}&{}".format(
            query, tweet_fields
        )
        return url

    def connect_to_endpoint(self, url, headers):
        response = requests.request("GET", url, headers=headers)
        print(response.status_code)
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
        return response.json()
'''