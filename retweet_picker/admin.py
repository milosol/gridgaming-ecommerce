from django.contrib import admin

from .models import (
    TwitterGiveaway,
    ContestUserParticipation,
    ContestUserAccounts,
    TwitterGiveawayID,
    GiveawayResults,
    GiveawayStats,
    GiveawayQueue,
    GiveawayWinners,
    DrawPrice,
    PricingPlan,
    Membership,
    Upgradeorder
)
from users.models import User

#TODO Add to giveaway queue eventually

# def get_context_data(self, *args, **kwargs):
#     # Call the base implementation first to get a context
#     context = super().get_context_data(**kwargs)
#     # queue_type = self.kwargs.get('queue_type', 'default')
#     # print("================ queue_type:", queue_type)
#     rows = GiveawayQueue.objects.all()
#     for row in rows:
#         try:
#             u = User.objects.get(id=row.user_id)
#             row.username = u.username
#         except Exception as e:
#             print(e)
#             row.username = ""
#         try:
#             order_item = OrderItem.objects.get(id=row.item_id)
#             row.itemname = order_item.get_title()
#         except Exception as e:
#             print(e)
#             row.itemname = ""
#         if row.start_time == None:
#             row.start_time = ''
#         if row.end_time == None:
#             row.end_time = ''
#         if row.tweet_url == None:
#             row.tweet_url = ''
#             row.tweet_id = ''
#         else:
#             row.tweet_id = row.tweet_url.split('status/')[1]

class GiveawayQueueAdmin(admin.ModelAdmin):
    list_display = [
        'user_id',
        'giveaway_amount',
        'status',
        'tweet_url',
        'created_at',
        'start_time',
        'end_time'
    ]

class TwitterGiveawayIDAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tweet_url',
        'giveaway_id',
    ]
    
class ContestUserParticipationAdmin(admin.ModelAdmin):
    list_display = [
        'contest_id',
        'tweet_url',
        'kind',
    ]
    
    def tweet_url(self, obj):
        return str(obj.contest.tweet_url)
    
    
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

class GiveawayWinnersAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_id',
        'user_name',
        'giveaway_id_id',
        'status',
        'draw_id',
        'retweet_count',
        'toload_count',
        'loaded_count',
        'winners',
        'tweet_url',
        'winner_count',
        'bot_chk',
        'follow_main',
        'followers',
    ]
    
    list_display_links = [
        'id',
        'tweet_url'
    ]
    
    def user_name(self, obj):
        u = User.objects.get(id=obj.user_id)
        return u.username
        
    def tweet_url(self, obj):
        return obj.get_tweet_url()
    
    def winners(self, obj):
        wins = obj.get_winners()
        if len(wins) > 0:
            return ', '.join(wins)
        else:
            return ''
        
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = [
        'plan',
        'label',
        'price',
        'limit_times',
        'unlimited_times',
        'credit_amount'
    ]

class MembershipAdmin(admin.ModelAdmin):
    list_display = [
        'user_id',
        'user_name',
        'credit_amount',
        'plan',
        'paid_month',
        'paid_time',
        'end_time',
        'bonus_count',
        'done_month',
        'done_count',
    ]  
 
    def user_name(self, obj):
        try:
            u = User.objects.get(id=obj.user_id)
            return u.username
        except Exception as e:
            print(e)
            return ''
        
class UpgradeorderAdmin(admin.ModelAdmin):
    list_display = [
        'user_id',
        'reason',
        'amount',
        'months',
        'upgradeto',
        'gwid',
        'payment',
        'payment_status',
        'created_at',
    ]
    
admin.site.register(TwitterGiveaway)
admin.site.register(ContestUserAccounts)
admin.site.register(TwitterGiveawayID, TwitterGiveawayIDAdmin)
admin.site.register(GiveawayResults)
admin.site.register(DrawPrice)
admin.site.register(ContestUserParticipation, ContestUserParticipationAdmin)
admin.site.register(GiveawayStats, GiveawayStatsAdmin)
admin.site.register(GiveawayQueue, GiveawayQueueAdmin)
admin.site.register(GiveawayWinners, GiveawayWinnersAdmin)
admin.site.register(PricingPlan, PricingPlanAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(Upgradeorder, UpgradeorderAdmin)

