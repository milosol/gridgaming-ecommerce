from django.db import models
from django.conf import settings
from users.models import User
# Create your models here.

class ProfileAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    days_old = models.IntegerField(null=True, blank=True)
    follower_count = models.IntegerField(null=True, blank=True)
    tweet_count = models.IntegerField(null=True, blank=True)
    favorites = models.IntegerField(null=True, blank=True)
    following = models.IntegerField(null=True, blank=True)
    default_profile_status = models.BooleanField(default=True)
    default_profile_image = models.BooleanField(default=False)
    unique_background = models.BooleanField(default=False)
    protected = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    giveaway_timeline_analysis = models.FloatField(default=0, null=True)
    tweets_per_day = models.FloatField(default=0, null=True)
    bot_prediction = models.BooleanField(default=False)
    profile_grade = models.CharField(null=True, max_length=2)
    date_analyzed = models.DateTimeField(auto_now_add=True)


class ProfileJudgement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    decision = models.BooleanField(default=False)
    profile_analysis = models.ForeignKey(ProfileAnalysis, on_delete=models.CASCADE)
    date_analyzed = models.DateTimeField(auto_now_add=True)