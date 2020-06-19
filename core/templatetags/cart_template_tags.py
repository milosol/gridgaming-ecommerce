from django import template
from core.models import Order

register = template.Library()


@register.filter
def cart_item_count(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False)
        if qs.exists():
            return qs[0].items.count()
    return 0

@register.filter
def cart_items(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False)
        if qs.exists():
            return qs[0].items.all()
    return None

def adjusted_price(giveaway_value, giveaway_fee, fee_quantifier):
    return giveaway_value + (giveaway_fee * fee_quantifier)

