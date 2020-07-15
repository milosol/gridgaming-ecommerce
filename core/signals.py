from django.shortcuts import get_object_or_404
from .models import Order, Payment, History
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
import random
import string

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
 
@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    ipn = sender
    print("------ pay note: " , ipn.payment_status)
    if ipn.payment_status == 'Completed':
        # payment was successful
        order_id = ipn.invoice.split("_")[0]
        kind =ipn.invoice.split("_")[1]
        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.all()
        order_items.update(ordered=True)
        for item in order_items:
            item.save()
            
        payment = Payment()
        payment.payment_method = 'P'
        payment.user = order.user
        payment.amount = order.get_total()
        payment.save()

        order.ordered = True
        order.status = 'P'
        order.payment = payment
        order.ref_code = create_ref_code()
        order.save()
        History.objects.create(user=order.user, action='Purchased', item_str=order.get_purchased_items(), 
                               reason="Payment done", order_str=order.id)
            