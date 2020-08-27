from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.shortcuts import reverse
from django.utils import timezone
from django_countries.fields import CountryField

CATEGORY_CHOICES = (
    ('GW', 'Giveaway'),
    ('PW', 'Pick Winner'),
    ('SB', 'Social Boost'),
    ('PE', 'Profile Examine')
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('I', 'info'),
    ('W', 'success'),
    ('D', 'danger')
)

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)

GIVEAWAY_STATUS_CHOICES = (
    ('I', 'In Cart'),
    ('P', 'Purchased'),
    ('S', 'Scheduled'),
    ('L', 'Live'),
    ('T', 'Winner Selected'),
    ('C', 'Winner Contacted'),
    ('D', 'Winner Paid')
)

SCHEDULER_QUEUE = (
    ('D', 'default'),
    ('L', 'low'),
    ('H', 'high')
)

PAYMENT_METHOD = (
    ('S', 'Stripe'),
    ('B', 'Braintree'),
    ('P', 'Paypal'),
    ('C', 'Bitcoin')
)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_profile')
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    braintree_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)
    twitch_account = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.user.username


class Socials(models.Model):
    twitter = models.BooleanField(default=False)
    instagram = models.BooleanField(default=False)
    facebook = models.BooleanField(default=False)
    tiktok = models.BooleanField(default=False)
    # TODO ADD MORE SOCIALS
    # Could also integrate with socialauth so they have to have it confirmed before checkout


class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    giveaway_value = models.FloatField(verbose_name="Amount to giveaway")  # Split value and fee to show amount given
    giveaway_fee = models.FloatField(verbose_name="Amount to charge buyer")
    duration_to_run = models.IntegerField(blank=True, null=True)
    #promote_socials = models.
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug = models.SlugField()
    available = models.BooleanField(default=True)
    priority = models.CharField(choices=SCHEDULER_QUEUE, max_length=1, default='D')
    description = models.TextField()
    image = models.ImageField()

    class Meta:
        default_related_name = 'items'
        ordering = ['-price']

    def __str__(self):
        return self.title

    def get_price(self):
        return self.giveaway_fee + self.giveaway_value

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey("Item", on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(default=1)
    available_to_run = models.IntegerField(default=1)
    kind = models.IntegerField(default=0)
    slot = models.ForeignKey("Slotitem", on_delete=models.CASCADE, null=True)
    username = models.CharField(max_length=200, default='')
    launch_code = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=GIVEAWAY_STATUS_CHOICES, default='I', blank=True, null=True)
    
    class Meta:
        ordering = ['-orders__id']
        
    def __str__(self):
        if self.kind == 0:
            return f"{self.quantity} of {self.item.title}"
        else:
            return f"{self.quantity} of {self.slot.title}"

    def get_title(self):
        if self.kind == 0:
            return self.item.title
        else:
            return self.slot.title
            
    def get_total_item_price(self):
        # self.user.related_field
        # self.user.account_type
        if self.kind == 0:
            price = (self.user.account_type.fee_quantifier * self.item.giveaway_fee) + self.item.giveaway_value
            # return self.quantity * self.item.get_price()
            return self.quantity * price
        else:
            return 0

    def get_total_discount_item_price(self):
        if self.kind == 0:
            return self.quantity * self.item.discount_price
        else:
            return 0

    def get_amount_saved(self):
        if self.kind == 0:
            return self.get_total_item_price() - self.get_total_discount_item_price()
        else:
            return 0

    def get_final_price(self):
        if self.kind == 0:
            if self.item.discount_price:
                return self.get_total_discount_item_price()
            return self.get_total_item_price()
        else:
            return self.quantity * self.slot.value

    def decrease_available(self):
        self.available_to_run -= 1

    def increase_available(self):
        self.available_to_run += 1


def get_deadline():
    return timezone.now() + timedelta(days=5)


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    expires_on = models.DateTimeField(default=get_deadline)
    desired_giveaway_date = models.DateTimeField(default=timezone.now, blank=True)
    ordered_date = models.DateTimeField(auto_now_add=True)
    ordered = models.BooleanField(default=False)
    kind = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=GIVEAWAY_STATUS_CHOICES, default='I', blank=True, null=True)
    notes = models.TextField(blank=True, max_length=500)
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    billing_address = models.ForeignKey(
        'Address', related_name='billing_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey(
        'Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)

    '''
    1. Item added to cart
    2. Adding a billing address
    (Failed checkout)
    3. Payment
    (Preprocessing, processing, packaging etc.)
    4. Being delivered
    5. Received
    6. Refunds
    '''

    class Meta:
        default_related_name = 'orders'
        ordering = ['-id']
        
    def __str__(self):
        return self.user.username

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount
        return total

    def get_available_runs(self):
        # return ', '.join([x.item.title for x in self.items.all()])
        return ', '.join([x.item.title for x in self.items.filter(kind=0)])

    def get_purchased_items(self):
        # return ', '.join([x.item.title for x in self.items.all()])
        if self.kind == 0:
            return ', '.join([x.item.title for x in self.items.filter(kind=0)])
        else:
            return ', '.join([x.slot.title for x in self.items.filter(kind=1)])

    def get_items_sum(self):
        # return sum([y.quantity for y in self.items.all()])
        if self.kind == 0:
            return sum([y.quantity for y in self.items.filter(kind=0)])
        else:
            return sum([y.quantity for y in self.items.filter(kind=1)])
        


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    braintree_charge_id = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True, null=True)
    payment_method = models.CharField(choices=PAYMENT_METHOD, max_length=1)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        
    def __str__(self):
        if self.user:
            return self.user.username
        else:
            return ''
    


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    use_max = models.IntegerField(default=1)
    amount = models.FloatField()

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


class Transaction(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    token = models.CharField(max_length=120)
    order_id = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self):
        return self.order_id

    class Meta:
        ordering = ['-timestamp']

def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = UserProfile.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)

# Create your models here.
class Slotitem(models.Model):
    title = models.CharField(max_length=200)
    available_count = models.IntegerField(default=20)
    available = models.BooleanField(default=True)
    total = models.IntegerField(default=20)
    points = models.IntegerField(default=100)
    placeholder = models.CharField(default='Enter username', blank=True, null=True, max_length=250)
    value = models.IntegerField(default=25)
    image = models.ImageField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

class Checktime(models.Model):
    time = models.IntegerField(default=5)
    launch_time = models.IntegerField(default=24)
    launched = models.BooleanField(default=False)
    status = models.IntegerField(default=0)
    launch_code = models.CharField(max_length=200, blank=True, null=True)
    action_time = models.DateTimeField(auto_now=False, null=True, blank=True)
    thread_id = models.IntegerField(default=1)
    cartcounter_run = models.BooleanField(default=False)
    def __str__(self):
        return str(self.time)
    
    def get_deadline(self):
        return self.action_time + timedelta(hours=self.launch_time)

class History(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, blank=True, null=True)
    action = models.CharField(max_length=200)
    start_date = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=200)
    item_str = models.CharField(max_length=200)
    order_str = models.CharField(max_length=100)
    other = models.CharField(max_length=200)
    
    def __str__(self):
        if self.user:
            return self.user.username + " : " + self.action
        else:
            return self.action
    
    class Meta:
        ordering = ['-id']
        
class Counting(models.Model):
    user_id = models.IntegerField(default=0)
    order_id = models.IntegerField(default=0)
    pause = models.BooleanField(default=False)
    deadline = models.DateTimeField(auto_now=False)
    def __str__(self):
        return str(self.user_id)

class Cartget(models.Model):
    user_id = models.IntegerField(default=0)
    def __str__(self):
        return str(self.user_id)