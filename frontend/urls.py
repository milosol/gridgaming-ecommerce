from django.urls import path, include, re_path
from .views import index, home, profile, account_type, update_account_type, pre_checkout, CheckoutView, PaypalPaymentView, payment_canceled, StripePaymentView
from django.contrib.auth.decorators import login_required

app_name = 'frontend'

urlpatterns = [
    # path('', index, name='index'),
    path('', home, name='home'),
    path('profile', profile, name='profile'),
    path('profile/account_type', account_type, name='account_type'),
    path('profile/update_account_type', update_account_type, name='update_account_type'),
    path('pre_checkout', pre_checkout, name='pre_checkout'),
    path('checkout', login_required(CheckoutView.as_view()), name='checkout'),
    path('paypalpayment', login_required(PaypalPaymentView.as_view()), name='paypalpayment'),
    path('stripepayment', login_required(StripePaymentView.as_view()), name='stripepayment'),
    path('payment_canceled', payment_canceled, name='payment_canceled'),
    re_path(r'^paypal/',include('paypal.standard.ipn.urls')),
]
