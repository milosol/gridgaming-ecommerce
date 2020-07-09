from django.shortcuts import render_to_response
from django.urls import path, re_path, include
from django.contrib.auth.decorators import login_required
from .views import (
    ItemDetailView,
    CheckoutViewV2,
    HomeView,
    OrderSummaryView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    #PaymentStripeView,
    #PaymentMainView,
    AddCouponView,
    RequestRefundView,
    OrderView,
    AllOrderView,
    DisableView,
    AccountView,
    PaypalPaymentProcess,
    payment_done,
    payment_canceled,
)

app_name = 'core'

urlpatterns = [
    path('', login_required(HomeView.as_view()), name='home'),
    path('checkout/', login_required(CheckoutViewV2.as_view()), name='checkout'),
    path('order-summary/', login_required(OrderSummaryView.as_view()), name='order-summary'),
    path('orders/', login_required(OrderView.as_view()), name='user-orders'),
    path('all-orders/', login_required(AllOrderView.as_view()), name='all-orders'),
    path('accounts/', login_required(AccountView.as_view()), name='accounts'),
    path('disable/', login_required(DisableView.as_view()), name='disable'),
    path('product/<slug>/', login_required(ItemDetailView.as_view()), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', login_required(AddCouponView.as_view()), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    #path('payment/', login_required(PaymentStripeView.as_view()), name='payment-stripe'),
    path('payment/', login_required(PaymentView.as_view()), name='payment'),
    path('request-refund/', login_required(RequestRefundView.as_view()), name='request-refund'),
    re_path(r'^paypal/',include('paypal.standard.ipn.urls')),
    re_path(r'^process/$', login_required(PaypalPaymentProcess.as_view()), name='process'),
    re_path(r'^done/$', payment_done, name='done'),
    re_path(r'^canceled/$', payment_canceled, name='canceled')

]

def handler404(request, template_name="404.html"):
    response = render_to_response(template_name)
    response.status_code = 404
    return response