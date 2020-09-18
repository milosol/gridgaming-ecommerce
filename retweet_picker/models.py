# from django.contrib.auth.models import User
# from users.models import GridUser as User
from core.models import Order, OrderItem
from django.conf import settings
from django.db import models
import uuid

STATUS_CHOICES = (
    ('W', 'Waiting'),
    ('L', 'Live'),
    ('R', 'Retrieve'),
    ('C', 'Choosed Winner'),
    ('E', 'End')
)
TYPE_CHOICES = (
    ('D', 'Default'),
    ('L', 'Low'),
    ('H', 'High')
)

class ContestUserAccounts(models.Model):
    """ Store all users within a single table and reference"""
    user_id = models.CharField(max_length=100, primary_key=True)
    user_handle = models.CharField(max_length=250, blank=True, null=True)
    user_screen_name = models.CharField(max_length=250)  # This is where winner will be pulled from
    location = models.CharField(max_length=200, blank=True, null=True)
    account_created = models.DateTimeField()

    def __str__(self):
        return self.user_screen_name


class GiveawayStats(models.Model):
    order = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True)
    # Reference user object through order
    giveaway_id = models.ForeignKey('TwitterGiveawayID', related_name='giveaway_stats', on_delete=models.CASCADE)
    giveaway_start_time = models.DateTimeField(null=True, blank=True)
    giveaway_end_time = models.DateTimeField(null=True, blank=True)
    sponsor_start_follower_count = models.IntegerField(null=True, blank=True)
    sponsor_end_follower_count = models.IntegerField(null=True, blank=True)
    retweet_count = models.IntegerField(null=True, blank=True)
    winner = models.ForeignKey(ContestUserAccounts, on_delete=models.CASCADE, null=True)
    # winner_handle = models.CharField(max_length=255, blank=True, null=True)
    confirmation_tweet = models.URLField(verbose_name='Confirmation Tweet', blank=True, null=True)


class TwitterGiveawayID(models.Model):
    """ Tweet URL and owner who created the tweet. Generates unique Contest ID"""
    tweet_url = models.URLField(max_length=500, unique=True)
    giveaway_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="giveaway_owner", on_delete=models.CASCADE, null=True)
    # giveaway_id = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.giveaway_id)


class ContestUserParticipation(models.Model):
    contestants = models.ManyToManyField(ContestUserAccounts)
    contest = models.OneToOneField('TwitterGiveawayID', unique=True, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.contest.tweet_url)
    # retweeted_on = models.DateTimeField(verbose_name="Date User Entered")


class TwitterGiveaway(models.Model):
    """ Form for sponsor/subscriber to fill out - dated model (based on code)"""
    # This will be used to track the form
    #TODO Will need to populate eventually
    tweet_url = models.OneToOneField('TwitterGiveawayID', unique=True, related_name='original_url',
                                     on_delete=models.CASCADE)
    winner_count = models.IntegerField(default=1)
    members_to_follow = models.CharField(max_length=64, blank=True)
    contest_name = models.CharField(max_length=100, default='DNP3 Giveaway')
    giveaway_id = models.ForeignKey(TwitterGiveawayID, related_name='giveaway_info', on_delete=models.CASCADE)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="retweet_winners", on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def giveaway_owner(self):
        return self.owner

    def __str__(self):
        return str(f'{self.contest_name} by {self.owner}')


class GiveawayWinners(models.Model):
    """ Table to track all winners - might not need if we use M2M"""
    giveaway_id = models.ForeignKey('TwitterGiveawayID', related_name='draw_giveaway_details', null=True, on_delete=models.SET_NULL)
    winner = models.ManyToManyField(ContestUserAccounts, related_name='draw_giveaway_winner')
    re_rolls = models.ManyToManyField('ContestUserAccounts', related_name='draw_rerolled_user')
    participants = models.IntegerField(null=True)  # Count of total entries
    created_at = models.DateTimeField(auto_now_add=True)

    def get_winners(self):
        win_names = []
        for w in self.winner.all():
            win_names.append(w.user_screen_name)
        return win_names

    def get_rerolls(self):
        reroll_names = []
        for r in self.re_rolls.all():
            reroll_names.append(r.user_screen_name)
        return reroll_names

class GiveawayResults(models.Model):
    """ Results of a giveaway - """
    giveaway_id = models.ForeignKey('TwitterGiveawayID', related_name='giveaway_details', null=True, on_delete=models.SET_NULL)
    winner = models.ForeignKey('ContestUserAccounts', null=True, on_delete=models.SET_NULL,
                               related_name='giveaway_winner')
    re_rolls = models.ManyToManyField('ContestUserAccounts', related_name='rerolled_user')
    participants = models.IntegerField(null=True)  # Count of total entries
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.winner:
            return str(self.winner)
        # else:
        #     return str(self.giveaway_id.giveaway_id)


class GiveawayQueue(models.Model):
    user_id = models.IntegerField(default=0)
    order_id = models.IntegerField(default=0)
    item_id = models.IntegerField(default=0)
    status = models.CharField(choices=STATUS_CHOICES, max_length=1)
    giveaway_amount = models.IntegerField(default=0)
    queue_type = models.CharField(choices=TYPE_CHOICES, max_length=1)
    duration = models.IntegerField(default=0)
    tweet_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(auto_now=False, null=True)
    end_time = models.DateTimeField(auto_now=False, null=True)
    
    class Meta:
        ordering = ['id']
        
    def __str__(self):
        return str(self.tweet_url)

