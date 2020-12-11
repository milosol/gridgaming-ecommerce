from background_task import background
from django.utils import timezone

from retweet_picker.bot_check import BotCheck


#@background(schedule=timezone.now())
def profile_checker(username=None):
    print(f'Performing analysis for {username}')
    profile_analysis = {'user':username}
    try:
        bc = BotCheck(username=username)
        res = bc.build_profile()
        res['bot_prediction'] = bc.bot_prediction()
        #res['bot_prediction'] = True
        profile_analysis.update(res)
        return profile_analysis
    #  TODO Add information to user record and save
    except Exception as e:
        print(f'{username} could not be analyzed...')
        pass
