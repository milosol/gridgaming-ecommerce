from django import template
from core.models import Order

register = template.Library()


@register.filter
def cart_item_count(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False, kind=0)
        if qs.exists():
            return qs[0].items.filter(kind=0).count()
            # return qs[0].items.count()
    return 0

@register.filter
def cart_items(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False, kind=0)
        if qs.exists():
            return qs[0].items.filter(kind=0)
            # return qs[0].items.all()
    return None

def adjusted_price(giveaway_value, giveaway_fee, fee_quantifier):
    return giveaway_value + (giveaway_fee * fee_quantifier)

intervals = (
    ('weeks', 10080),
    ('days', 1440),
    ('hours', 60),
    ('minutes', 1),
    )

@register.filter
def display_time(minutes, granularity=3):
    """ Creates """
    minutes = int(minutes)
    result = []

    for name, count in intervals:
        print(minutes, name, count)
        value = minutes // count
        print(value)
        if value:
            minutes -= value * count
            print('minutes', minutes)
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])