from django.contrib import admin

from .models import (
    TwitterGiveaway,
    ContestUserParticipation,
    ContestUserAccounts,
    TwitterGiveawayID,
    GiveawayResults,
    GiveawayStats
)

# Register your models here.
class GiveawayStatsAdmin(admin.ModelAdmin):

    list_display = [
        'get_order',
        'get_ref_code',
        'giveaway_start_time',
        'giveaway_end_time',
        'sponsor_start_follower_count',
        'sponsor_end_follower_count',
        'retweet_count',
        'winner',
        'confirmation_tweet'
    ]

    class Meta:
        verbose_name = 'Giveaway Stat'
        verbose_name_plural = "Giveaway Stats"

    def get_order(self, obj):
        return obj.order.user

    def get_ref_code(self, obj):
        return obj.order.ref_code

    get_order.short_description = "Giveaway Order"
    get_ref_code.short_description = "Reference Code"

    #search_fields = ['order__user']

admin.site.register(TwitterGiveaway)
admin.site.register(ContestUserAccounts)
admin.site.register(TwitterGiveawayID)
admin.site.register(GiveawayResults)
admin.site.register(ContestUserParticipation)
admin.site.register(GiveawayStats, GiveawayStatsAdmin)

