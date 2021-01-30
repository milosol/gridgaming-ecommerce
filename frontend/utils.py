from allauth.socialaccount.models import SocialAccount
from .svg_icons import discord, twitch, youtube, twitter
from .models import OneValue
from retweet_picker.models import Membership

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