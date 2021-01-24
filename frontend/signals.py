from django.shortcuts import get_object_or_404
from retweet_picker.models import Upgradeorder, Membership
from core.models import Payment
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
import random
import string
from users.models import User
from django.utils import timezone
from datetime import timedelta
from .views import add_drawcount, bought_credit
from .models import BuyCredit

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    try:
        ipn = sender
        print("------ pay note: ", ipn.payment_status)
        if ipn.payment_status == 'Completed' or ipn.payment_status == 'Pending':
            # payment was successful
            bcid = ipn.invoice.split("_")[2]
            bc = get_object_or_404(BuyCredit, id=bcid)
            if bc.payment_status == 'W':
                payment = Payment()
                payment.payment_method = 'P'
                payment.user = bc.user
                payment.amount = bc.usd_amount
                payment.save()
                bc.payment = payment
                bc.payment_status = ipn.payment_status[0]
                bc.save()
                bought_credit(bc.id)
                # if uo.reason == 'membership':
                #     membership = get_object_or_404(Membership, user_id=uoid.user_id)
                #     membership.plan = uo.upgradeto
                #     membership.paidmonth = uo.months
                #     membership.paid_time = timezone.now()
                #     membership.end_time = membership.paid_time + timedelta(days=uo.months*30)
                #     membership.done_count = 0
                #     membership.done_month = 0
                #     membership.save()
                # else:
                #     add_drawcount(bc.id)
            else:
                bc.payment_status = ipn.payment_status[0]
                bc.save()
                
    except Exception as e:
        print(e)
