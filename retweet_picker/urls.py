from django.urls import path

from . import views
from .views import (
    #GiveawayResultsListView
    OrdersListView,
    launch_giveaway,
    decoder_ring,
    #prelaunch_validator,
    order_details
)

app_name = 'retweet_picker'

urlpatterns = [
    path('', OrdersListView.as_view(), name='giveaway-list'),
    path('new_contest/', views.new_retweet_contest, name='retweet_picker'),
    path('launch/<int:order_id>/<int:item_id>', launch_giveaway, name='launch_giveaway'),
    path('order/<int:order_id>', order_details, name="order_details"),
    path('results/<int:order_id>', views.contest_results, name='contest_results'),
    #path('results/<uuid:giveaway_id>', views.contest_results, name='contest_results'),
    path('results/', views.contest_results, name='all_contest_results'),
    path('bubble_rescue/decoder_ring/<slug:secret_code>/', views.decoder_ring, name='decoder'),
    path('bubble_rescue/', views.bubble_rescue, name='bubble-rescue-5000')
]
