from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'profile_analyzer'

urlpatterns = [
    path('', views.main, name='profile-analyzer'),
    path('profile/', views.analyze_profile, name='analyze-profile'),
]
