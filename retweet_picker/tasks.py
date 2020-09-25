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
                                     user_id=None, order_id=None, giveaway_amount=0, sponsors=None):
    from django.db import connection
    connection.close()
    gm = GiveawayManager(user_id=user_id, order_id=order_id,
                         existing_tweet_url=existing_tweet_url, 
                         new_giveaway=False, giveaway_amount=giveaway_amount, sponsors=sponsors)
    gm.run_pipeline()
    
def fetch_content_from_url(existing_tweet_url=None):
    # from django.db import connection
    # connection.close()
    res = {'success': True, 'msg': ''}
    try:
        gm = GiveawayManager(new_giveaway=False, existing_tweet_url=existing_tweet_url)
        if gm.tweet_id:
            res['tweet_id'] = gm.tweet_id
        else:
            res['success'] = False
            res['msg'] = "Can't process this url. Are you sure this url is correct?"
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = "Can't process this url. Are you sure this url is correct?"
    return res

def draw_winner(existing_tweet_url=None, winner_count=1, actions=None, user_id=None):
    # from django.db import connection
    # connection.close()
    gm = GiveawayManager(new_giveaway=False, existing_tweet_url=existing_tweet_url, winner_count=winner_count, sponsors=actions['sponsors'], user_id=user_id)
    res = gm.drawwinner(actions=actions)
    print(" == draw result:", res)
    return res
        
@job('default')
def sleeper():
    from django.db import connection
    connection.close()
    print('sleeping for 10 sec')
    time.sleep(10)
