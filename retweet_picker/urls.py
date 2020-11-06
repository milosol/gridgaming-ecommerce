from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views
from .views import (
    OrdersListView,
    launch_giveaway,
    #prelaunch_validator,
    order_details,
    QueueListView,
    delete_queue,
    clear_queue,
    pick, draw, drawstop, fetch_data, import_contest, pick_entries, load_entries, load_entry_progress,
    load_all_entries, drawing_progress, draw_verify
)

app_name = 'retweet_picker'

urlpatterns = [
    path('', OrdersListView.as_view(), name='giveaway-list'),
    path('new_contest/', views.new_retweet_contest, name='retweet_picker'),
    path('launch/<int:order_id>/<int:item_id>', launch_giveaway, name='launch_giveaway'),
    path('queue/', QueueListView.as_view() , name='queue_view'),
    # path('queue/<str:queue_type>/', QueueListView.as_view() , name='queue_view'),
    path('delqueue', delete_queue , name='del_queue'),
    path('draw', draw , name='draw'),
    path('draw_verify', draw_verify , name='draw_verify'),
    path('drawstop', drawstop , name='drawstop'),
    path('drawing_progress', drawing_progress , name='drawing_progress'),
    path('fetch_data', fetch_data , name='fetch_data'),
    path('import_contest', import_contest , name='import_contest'),
    path('load_entries', load_entries , name='load_entries'),
    path('load_entry_progress', load_entry_progress , name='load_entry_progress'),
    path('load_all_entries', load_all_entries , name='load_all_entries'),
    path('draw/<int:gwid>', login_required(pick_entries) , name='pick_entries'),
    path('clearqueue', clear_queue , name='clear_queue'),
    path('order/<int:order_id>', order_details, name="order_details"),
    path('results/<int:order_id>', views.contest_results, name='contest_results'),
    #path('results/<uuid:giveaway_id>', views.contest_results, name='contest_results'),
    path('results/', views.contest_results, name='all_contest_results'),
    path('bubble_rescue/decoder_ring/<slug:secret_code>/', views.decoder_ring, name='decoder'),
    path('bubble_rescue/', views.bubble_rescue, name='bubble-rescue-5000'),
    path('import/', login_required(views.pick), name='pick')
]
