from allauth.socialaccount.models import SocialAccount
from .svg_icons import discord, twitch, youtube, twitter


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