from django.urls import path, include
from .views import index, home, profile, account_type, update_account_type

app_name='frontend'

urlpatterns = [
    #path('', index, name='index'),
    path('', home, name='home'),
    path('profile', profile, name='profile'),
    path('profile/account_type', account_type, name='account_type'),
    path('profile/update_account_type', update_account_type, name='update_account_type' )
]