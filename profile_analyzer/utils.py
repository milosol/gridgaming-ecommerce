from retweet_picker.bot_check import BotCheck, p2f
from profile_analyzer.models import ProfileAnalysis, ProfileJudgement

# def return_user_profile(username):
#     dnp_p = BotCheck(username=username)
#     p = dnp_p.build_profile()
#     #user = User.objects.get(id=3) #request.user.id
#     profile_analysis = ProfileAnalysis.objects.create(user=user, **p)
#     return profile_analysis

def update_or_create_analyzer(user_obj, profile_analysis):
    obj, created = ProfileJudgement.objects.update_or_create(user=user_obj,
                                       defaults={'decision': profile_analysis.bot_prediction,
                                                 'profile_analysis': profile_analysis}
                                      )
    # if not created:
    #     # Remove one credit after analysis was ran
    #     obj.credits -= 1
    #     obj.save()
    return obj