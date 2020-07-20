# from allauth.socialaccount.signals import (
#     pre_social_login,
#     social_account_added,
#     social_account_removed,
#     social_account_updated
# )
# from allauth.account.signals import (
#     email_confirmed,
#     user_signed_up,
#     user_logged_in,
#     user_logged_out
# )
#
# from django.dispatch import receiver
# from django.contrib.auth.models import User
# from users.models import User
# from core.models import History


# @receiver(user_signed_up)
# def populate_profile(sociallogin, user, **kwargs):
#
#     if sociallogin.account.provider == 'twitter':
#         user_data = user.socialaccount_set.filter(provider='twitter')[0].extra_data
#         #picture_url = user_data['profile_image_url']
#         #picture_url = picture_url.rsplit("_", 1)[0] + "." + picture_url.rsplit(".", 1)[1]
#         email = user_data['email']
#         #first_name = user_data['name'].split()[0]
#
#     user.profile.email_address = email
#     #user.profile.first_name = first_name
#     user.profile.save()
