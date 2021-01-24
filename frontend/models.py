from core.models import Order, OrderItem, Payment               
from django.conf import settings
from django.db import models
import uuid

PAYMENT_CHOICES = (
    ('W', 'Waiting'),
    ('P', 'Pending'),
    ('C', 'Complete'),
)

class BuyCredit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True, null=True)
    credit_amount = models.IntegerField(default=0)
    usd_amount = models.FloatField(default=0)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    payment_status = models.CharField(choices=PAYMENT_CHOICES, max_length=1, default='W')
    added_credit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']

class OneValue(models.Model):
    cc_per_usd = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['id']
