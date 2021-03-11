# from django.contrib.auth.models import User
# from users.models import GridUser as User
from core.models import Order, OrderItem, Payment               
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

DRAWSTATUS_CHOICES = (
    ('C', 'Created'),
    ('E', 'Loading Error'),
    ('L', 'Loaded entries'),
    ('D', 'Drawing'),
    ('S', 'Drawing stoped'),
    ('W', 'Drawed')
)

PRICINGPLAN_CHOICES = (
    ('F', 'Free'),
    ('B', 'Basic'),
    ('P', 'Pro')
)
PAYMENT_CHOICES = (
    ('W', 'Waiting'),
    ('P', 'Pending'),
    ('C', 'Complete'),
)

class ContestUserAccounts(models.Model):
    """ Store all users within a single table and reference"""
    user_id = models.CharField(max_length=100, primary_key=True)
    user_handle = models.CharField(max_length=250, blank=True, null=True)
    user_screen_name = models.CharField(max_length=250)  # This is where winner will be pulled from
    location = models.CharField(max_length=200, blank=True, null=True)
    profile_img = models.URLField(max_length=500, blank=True, null=True)
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
    contest = models.ForeignKey('TwitterGiveawayID', on_delete=models.CASCADE)
    kind = models.IntegerField(default=0)

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

class DrawPrice(models.Model):
    free_max = models.IntegerField(default=500)
    price = models.IntegerField(default=1)
    per_amount = models.IntegerField(default=100)
    queue_count = models.IntegerField(default=3)
    
class Rerolls(models.Model):
    reason = models.CharField(max_length=200, blank=True)
    contestant = models.ForeignKey(ContestUserAccounts, on_delete=models.CASCADE)  
    kind = models.IntegerField(default=0) # 0: reason  1: choosing  2:choosed  3: rerolled
    class Meta:
        ordering = ['id']
        
       
class GiveawayWinners(models.Model):
    """ Table to track all winners - might not need if we use M2M"""
    giveaway_id = models.ForeignKey('TwitterGiveawayID', related_name='draw_giveaway_details', null=True, on_delete=models.SET_NULL)
    price = models.IntegerField(default=0)
    status = models.CharField(choices=DRAWSTATUS_CHOICES, max_length=1, default='C')
    load_error = models.CharField(max_length=200, blank=True)
    winner = models.ManyToManyField(ContestUserAccounts, related_name='draw_giveaway_winner', blank=True)
    re_rolls = models.ManyToManyField(Rerolls, blank=True)
    participants = models.IntegerField(null=True, blank=True)  # Count of total entries
    created_at = models.DateTimeField(auto_now_add=True)
    drawed_at = models.DateTimeField(null=True, blank=True)
    winner_count = models.IntegerField(default=1)
    follow_main = models.BooleanField(default=True)
    bot_chk = models.BooleanField(default=True)
    followers = models.CharField(max_length=250, blank=True)
    retweet_count = models.IntegerField(default=0)
    toload_count = models.IntegerField(default=0)
    loaded_count = models.IntegerField(default=0)
    paid_count = models.IntegerField(default=0)
    user_id = models.IntegerField(default=0)
    command = models.IntegerField(default=0)
    draw_id = models.CharField(max_length=50, blank=True)
    rerolled_count = models.IntegerField(default=0)
    class Meta:
        ordering = ['id']
        
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

    def get_tweet_url(self):
        tgid = TwitterGiveawayID.objects.get(id=self.giveaway_id_id)
        return tgid.tweet_url

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

class PricingPlan(models.Model):
    plan = models.CharField(choices=PRICINGPLAN_CHOICES, max_length=1)
    label = models.CharField(max_length=200, blank=True)
    price = models.IntegerField(default=1)
    limit_times = models.IntegerField(default=2)
    limit_count = models.IntegerField(default=10000000)
    unlimited_times = models.BooleanField(default=False)
    unlimited_count = models.BooleanField(default=True)
    reroll_count = models.IntegerField(default=10)
    credit_amount = models.IntegerField(default=1)
    class Meta:
        ordering = ['price']
        
    def __str__(self):
        return self.plan
    
class Membership(models.Model): 
    user_id = models.IntegerField(default=0)
    plan = models.CharField(choices=PRICINGPLAN_CHOICES, max_length=1, default='F')
    paid_month = models.IntegerField(default=0)
    paid_time = models.DateTimeField(auto_now=False, null=True, blank=True)
    end_time = models.DateTimeField(auto_now=False, null=True, blank=True)
    done_count = models.IntegerField(default=0)
    done_month = models.IntegerField(default=0)
    bonus_count = models.IntegerField(default=0)
    credit_amount = models.IntegerField(default=0)
    freecredit_donemonth = models.IntegerField(default=0)
    ended_alert = models.IntegerField(default=0)
    freecredit_alert = models.IntegerField(default=0)
    analyzed_time = models.DateTimeField(auto_now=False, null=True, blank=True)
     
    class Meta:
        ordering = ['id']
        
class Upgradeorder(models.Model):
    user_id = models.IntegerField(default=0)
    reason = models.CharField(max_length=50, blank=True, null=True)
    amount = models.IntegerField(default=0)
    months = models.IntegerField(default=0)
    upgradeto = models.CharField(choices=PRICINGPLAN_CHOICES, max_length=1, default='B')
    gwid = models.IntegerField(default=0)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    payment_status = models.CharField(choices=PAYMENT_CHOICES, max_length=1, default='W')
    created_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']
        

        