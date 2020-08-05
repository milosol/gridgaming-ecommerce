from django.urls import path

app_name = 'giveaways'

from giveaways.views import (
    GiveawayDetailView,
    GiveawayListView,
    GiveawayCreateView,
)

urlpatterns = [
    path("", GiveawayListView.as_view(), name="giveaway-list"),
    path("create", GiveawayCreateView.as_view(), name="giveaway-create"),
    #path("<int:pk>/", GiveawayDetailView.as_view(), name="giveaway-detail"),
    path(
        "<int:pk>-<str:slug>/",
        GiveawayDetailView.as_view(),
        name="giveaway-detail",
    ),

]