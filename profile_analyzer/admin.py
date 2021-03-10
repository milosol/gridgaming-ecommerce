from django.contrib import admin

# Register your models here.
from .models import *

class ProfileAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'days_old',
                    'follower_count',
                    'tweet_count',
                    'favorites',
                    'protected',
                    'suspended',
                    'tweets_per_day',
                    'profile_grade',
                    'bot_prediction',
                    'date_analyzed',
                    ]
    

class ProfileJudgementAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'decision',
                    'profile_analysis',
                    'date_analyzed',
                    ]
    list_display_links = [
        'user',
        'profile_analysis'
    ]
    
admin.site.register(ProfileAnalysis, ProfileAnalysisAdmin)
admin.site.register(ProfileJudgement, ProfileJudgementAdmin)