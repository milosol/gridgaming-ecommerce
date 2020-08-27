from django_rq import job
import time
from retweet_picker.manager import GiveawayManager


def start_giveaway_bg(user_id=None,
                      order_id=None,
                      sponsors=None,
                      giveaway_amount=None,
                      duration=None):
    from django.db import connection
    connection.close_if_unusable_or_obsolete()

    gm = GiveawayManager(
        user_id=user_id,
        order_id=order_id,
        sponsors=sponsors,
        giveaway_amount=giveaway_amount,
        duration=duration)

    gm.run_pipeline()
    return gm.tweet_url

def retrieve_tweets_choose_winner_job(existing_tweet_url=None,
                                     user_id=None, order_id=None, giveaway_amount=0):
    from django.db import connection
    connection.close()
    gm = GiveawayManager(user_id=user_id, order_id=order_id,
                         existing_tweet_url=existing_tweet_url, 
                         new_giveaway=False, giveaway_amount=giveaway_amount)
    gm.run_pipeline()


@job('default')
def sleeper():
    from django.db import connection
    connection.close()
    print('sleeping for 10 sec')
    time.sleep(10)
