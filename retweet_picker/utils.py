import re

from django.utils import timezone


def giveaway_ends(minutes=30):
    return timezone.now() + timezone.timedelta(minutes=minutes)

def id_from_url(url):
    digit = re.search('[\d+]{10,}', url)
    if digit:
        return digit.group(0)


intervals = (
    ('weeks', 10080),
    ('days', 1440),
    ('hours', 60),
    ('minutes', 1),
    )


def display_time(minutes, granularity=3):
    """ Creates """
    result = []

    for name, count in intervals:
        value = minutes // count
        if value:
            minutes -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])
