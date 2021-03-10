from allauth.socialaccount.models import SocialAccount
from .svg_icons import discord, twitch, youtube, twitter
from .models import OneValue
from retweet_picker.models import Membership, PricingPlan, PRICINGPLAN_CHOICES
from django.utils import timezone
import math

def get_cc_per_usd():
    try:
        if OneValue.objects.all().count() == 0:
            OneValue.objects.create()
        return OneValue.objects.all().first().cc_per_usd
    except Exception as e:
        print(e)
        return 1
    
def get_min_buy_credit():
    try:
        if OneValue.objects.all().count() == 0:
            OneValue.objects.create()
        return OneValue.objects.all().first().min_buy_credit
    except Exception as e:
        print(e)
        return 1

def get_judge_credit_price():
    try:
        if OneValue.objects.all().count() == 0:
            OneValue.objects.create()
        return OneValue.objects.all().first().judge_credit_price
    except Exception as e:
        print(e)
        return 1
    
def usd2credit(usd_value):
    cc = get_cc_per_usd()
    return cc * usd_value
    
def credit2usd(credit_value):
    cc = get_cc_per_usd()
    return round(credit_value / cc, 1)
    
def get_credit_amount(user_id):
    try:
        membership, created = Membership.objects.get_or_create(user_id=user_id)
        return membership.credit_amount
    except Exception as e:
        print(e)
        return 0

def credit_minus(user_id, amount):
    try:
        membership, created = Membership.objects.get_or_create(user_id=user_id)
        membership.credit_amount = max(membership.credit_amount - amount, 0)
        membership.save()
        return membership.credit_amount
    except Exception as e:
        print(e)
        return 0
    
def get_pricing_plans():
    result = {}
    try:
        if PricingPlan.objects.all().count() == 0:
            for choice, label in PRICINGPLAN_CHOICES:
                PricingPlan.objects.create(plan=choice, label=label)
        pps = PricingPlan.objects.all()
        for pp in pps:
            if pp.plan not in result:
                result[pp.plan] = pp.credit_amount
    except Exception as e:
        print(e)
    return result
    
def add_free_credit(user_id):
    res = 0
    try:
        mb, created = Membership.objects.get_or_create(user_id=user_id)
        pps = get_pricing_plans()
        if mb.plan in pps and mb.freecredit_donemonth <= mb.done_month:
            mb.freecredit_donemonth = mb.done_month + 1
            if pps[mb.plan] > 0:
                mb.credit_amount += pps[mb.plan]
                mb.freecredit_alert = 1
                res = pps[mb.plan]
            mb.save()
    except Exception as e:
        print("Error while adding free credit :", user_id)
        print(e)
    return res

def get_freecredit_amount(user_id):
    mb, created = Membership.objects.get_or_create(user_id=user_id)
    pps = get_pricing_plans()
    if mb.plan in pps:
        return pps[mb.plan]
    else:
        return 0
    
def set_donemonth(membership_id):
    try:
        membership = Membership.objects.get(id=membership_id)
        if membership.paid_time == None:
            membership.paid_time = timezone.now()
            
        diff = timezone.now() - membership.paid_time
        diff_month = math.floor(diff.total_seconds()/(3600*24*30))
        membership.analyzed_time = timezone.now()
        if membership.done_month != diff_month:
            membership.done_month = diff_month
            membership.done_count = 0
        if membership.done_month >= membership.paid_month and membership.plan == 'F':
            membership.plan = 'F'
            membership.paid_month = 0
            membership.done_count = 0
            membership.done_month = 0
            membership.freecredit_donemonth = 0
            membership.paid_time = timezone.now()
            membership.ended_alert = 1
            membership.freecredit_alert = 0
        membership.save()
    except Exception as e:
        print(e)
    
def user_membership(user_id):
    membership, created = Membership.objects.get_or_create(user_id=user_id)
    if created or membership.paid_time == None:
        membership.paid_time = timezone.now()
    if created or membership.analyzed_time == None:
        membership.analyzed_time = timezone.now()
    membership.save()
    return membership
       
def build_socials(self, user_id=None):
    all_services = ['discord', 'twitter', 'twitch', 'google']
    social_records = []
    data = SocialAccount.objects.filter(user=int(user_id))
    fa_mapping = {'discord': 'fab fa-discord',
                  'twitter': 'fab fa-twitter',
                  'twitch': 'fab fa-twitch',
                  'google': 'fab fa-google',
                  'grid': 'fas fa-compact-disc',
                  'epic': 'fas fa-globe'}

    svg_icons = {'discord': discord,
                 'twitch': twitch,
                 'google': youtube,
                 'twitter': twitter}

    for i, service in enumerate(data):
        record = {}
        if data[i].provider == 'discord':
            record = self.record_create(data[i].provider, data[i].extra_data['username'] + '#' + str(
                data[i].extra_data.get('discriminator')))
        if data[i].provider == 'twitter':
            record = self.record_create(data[i].provider, data[i].extra_data.get('screen_name'))
        if data[i].provider == 'twitch':
            record = self.record_create(data[i].provider, data[i].extra_data.get('display_name'))
        if data[i].provider == 'google':
            record = self.record_create(data[i].provider, data[i].extra_data.get('name'))
        if data[i].provider == 'paypal':
            record = self.record_create(data[i].provider, data[i].extra_data.get('email'))
        all_services.remove(data[i].provider)
        record.update({'status': 'connected'})
        social_records.append(record)


    return {'socials': social_records,
            'services_not_connected': all_services,
            'fa_mapping': fa_mapping,
            'svg_icons': svg_icons}