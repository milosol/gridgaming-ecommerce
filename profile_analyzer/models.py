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
    
    def __str__(self):
        if self.user:
            return str(self.user)
        else:
            return ''
        

class ProfileJudgement(models.Model):
    """
    Made to keep track of current status of users and how many times they can run
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    decision = models.BooleanField(default=False)
    credits = models.IntegerField(default=1) #Determines how many times they can run the checker
    profile_analysis = models.ForeignKey(ProfileAnalysis, on_delete=models.CASCADE, null=True, blank=True)
    date_analyzed = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.decision is True:
            return str(self.user) + ' is eligible'
        else:
            return str(self.user) + ' is not eligible'
