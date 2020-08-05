from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django.conf import settings
from django.utils import timezone
import pytz

PAYMENT_CHOICES = (
    ('P', 'Paypal'),
    ('C', 'Bitcoin'),
    ('S', 'Stripe'),
)


def present_or_future_date(value):
    "Check if date is not in the past"
    if value < timezone.now():
        raise forms.ValidationError("The date cannot be in the past!")
    return value


def giveaway_day_range(value):
    current_time_range = (timezone.now() - timezone.timedelta(hours=7)) + timezone.timedelta(
        days=settings.GIVEAWAY_DAY_RANGE)
    timezone_aware = current_time_range.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))
    if not timezone_aware >= value >= timezone.now():
        raise forms.ValidationError(f"Date must be within {settings.GIVEAWAY_DAY_RANGE} days!")
    return value


class CheckoutFormv2(forms.Form):
    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False)
    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)
    # desired_giveaway_date = forms.DateTimeField(required=False,
    #                                             widget=forms.TextInput(
    #                                                 attrs={'type': 'text',
    #                                                        'id':'date-format',
    #                                                        'class':'form-control datetimepicker',
    #                                                        'placeholder': 'Select Giveaway Date (within 5 days)'}
    #                                             ),
    #                                             input_formats=['%A %d %b %Y - %H:%S',
    #                                                            '%Y-%m-%dT%H:%M',
    #                                                            '%l %d %M %Y - %H:%i'],
    #                                             #TODO Add validator soon
    #                                             validators=[])
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(required=False)
    shipping_address2 = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)

    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False)
    set_default_shipping = forms.BooleanField(required=False)
    use_default_shipping = forms.BooleanField(required=False)
    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)

    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'basic-addon2'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()


class PaymentForm(forms.Form):
    braintreeToken = forms.CharField(required=False)
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)

class BitpayForm(forms.Form):
    invoice_id = forms.CharField(required=False)
    order_id = forms.CharField(required=False)
