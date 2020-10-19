from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'profile_analyzer'

urlpatterns = [
    path('', views.profile_analyzer, name='profile-analyzer'),
]
