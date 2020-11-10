# Create your models here.
import logging

# from allauth.account.utils import perform_login
# from allauth.socialaccount.signals import pre_social_login
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    account_type = models.ForeignKey("UserRoles",
                                     null=True,
                                     blank=True,
                                     on_delete=models.CASCADE)
    blacklisted = models.BooleanField(default=False)
    cleared_hot = models.BooleanField(default=False)  # Sets to true after member earns status


class UserRoles(models.Model):
    role_name = models.CharField(max_length=100, default="New User")
    role_description = models.CharField(max_length=500, null=True, blank=True)
    fee_quantifier = models.FloatField()  # Role to create quantifier based on user role
    time_quantifier = models.FloatField()

    def __str__(self):
        return self.role_name


class UserFeedback(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    feedback = models.TextField(verbose_name="User Feedback", max_length=1000)
    created_on = models.DateTimeField(auto_now_add=True)


from allauth.account.signals import (
    user_logged_in,
)
from django.dispatch import receiver
from core.models import History

# @receiver(pre_social_login)
# def link_to_local_user(sender, request, sociallogin, **kwargs):
#     email_address = sociallogin.account.extra_data['email']
#     users = User.objects.filter(email=email_address)
#     if users:
#         perform_login(request, users[0], email_verification=app_settings.EMAIL_VERIFICATION)


@receiver(user_logged_in)
def login_user(sociallogin, user, **kwargs):
    History.objects.create(user=user, action='Logged In')
    if sociallogin.account.provider == 'twitter':
        try:
            user.username = sociallogin.account.extra_data['screen_name']
            user.email = sociallogin.account.extra_data['email']
            user.save()
        except Exception as e:
            logging.error(f'Could not update user upon login: {e}')
