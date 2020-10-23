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
from .views import add_drawcount
def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    try:
        ipn = sender
        print("------ pay note: ", ipn.payment_status)
        if ipn.payment_status == 'Completed' or ipn.payment_status == 'Pending':
            # payment was successful
            uoid = ipn.invoice.split("_")[1]
            uo = get_object_or_404(Upgradeorder, id=uoid)
            if uo.payment_status == 'W':
                user = get_object_or_404(User, id=uo.user_id)
                payment = Payment()
                payment.payment_method = 'P'
                payment.user = user
                payment.amount = uo.amount
                payment.save()
                uo.payment = payment
                uo.payment_status = ipn.payment_status[0]
                uo.save()
                if uo.reason == 'membership':
                    membership = get_object_or_404(Membership, user_id=uoid.user_id)
                    membership.plan = uo.upgradeto
                    membership.paidmonth = uo.months
                    membership.paid_time = timezone.now()
                    membership.end_time = membership.paid_time + timedelta(days=uo.months*30)
                    membership.done_count = 0
                    membership.done_month = 0
                    membership.save()
                else:
                    add_drawcount(uo.id)
            else:
                uo.payment_status = ipn.payment_status[0]
                uo.save()
    except Exception as e:
        print(e)
