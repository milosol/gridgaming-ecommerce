import random
import string
import json
from django.http import HttpResponse
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, View
from paypal.standard.forms import PayPalPaymentsForm
from stripe import error
from bitpay.client import Client

from core.decorators import account_type_check
from slotapp.views import del_timing
from .forms import CheckoutFormv2, CouponForm, RefundForm, PaymentForm, BitpayForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, Slotitem, History
import logging
import traceback
# from core.extras import transact, generate_client_token


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutViewV2(View):

    def get(self, *args, **kwargs):
        # generate all other required data that you may need on the #checkout page and add them to context.
        kind = self.request.session.get('kind', 0)
        try:
            res = removefromcart(self.request)
            if res['removed'] == 1:
                messages.warning(self.request, res['msg'])
                return redirect("core:order-summary")
            order = Order.objects.get(user=self.request.user, ordered=False, kind=kind)
            form = CheckoutFormv2()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True,
                'kind': kind
            }

            context.update({'giveaway_day_range': settings.GIVEAWAY_DAY_RANGE})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "shop_v2/checkout.html", context)
        except ObjectDoesNotExist:
            # braintree_client_token = braintree.ClientToken.generate({})
            # context = {'braintree_client_token': braintree_client_token}
            messages.info(self.request, "You do not have an active order")
            if kind == 0:
                return redirect("core:order-summary")
            else:
                return redirect("slotapp:first_page")

    def post(self, *args, **kwargs):
        form = CheckoutFormv2(self.request.POST or None)
        try:
            kind = self.request.session.get('kind', 0)
            order = Order.objects.get(user=self.request.user, ordered=False, kind=kind)
            if form.is_valid():

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')

                if use_default_billing:
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        # print(order.desired_giveaway_date)
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    # print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment')
                elif payment_option == 'P':
                    return redirect('core:process')
                elif payment_option == 'C':
                    return redirect('core:bitpay')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
            else:
                modal_html = ''
                for k, v in form.errors.items():
                    modal_html += f'{k}: {v[0]}'
                messages.error(self.request, f'{modal_html}', extra_tags='html')
                return redirect("core:checkout")

        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


def get_user_pending_order(request):
    try:
        # get order for the correct user
        kind = request.session.get('kind', 0)
        # user_profile = get_object_or_404(UserProfile, user=request.user)
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        order = Order.objects.filter(user=user_profile.user, ordered=False, kind=kind)
        # order = Order.objects.filter(user=request.user, ordered=False, kind=kind)
        if order.exists():
            # get the only order in the list of filtered orders
            return order[0]
        
    except Exception as e:
        print("=== error occured while getting pending order")
        print(e)
        traceback.format_exc(e)
    return 0


class PaymentView(View):
    """
    View dedicated to handling payment for stripe
    """

    def get(self, *args, **kwargs):
        
        order = get_user_pending_order(self.request)
        # client_token = generate_client_token()
        try:
            if order != 0:
                if order.billing_address:
                    context = {
                        'order': order,
                        'DISPLAY_COUPON_FORM': False,
                        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
                        # 'client_token': client_token,
                        'client_token': create_ref_code(),
                    }
                    userprofile = self.request.user.user_profile
                    if userprofile.one_click_purchasing:
                        # fetch the users card list
                        cards = stripe.Customer.list_sources(
                            userprofile.stripe_customer_id,
                            limit=3,
                            object='card'
                        )
                        card_list = cards['data']
                        if len(card_list) > 0:
                            # update the context with the default card
                            context.update({
                                'card': card_list[0]
                            })
                    return render(self.request, "shop_v2/stripe.html", context)
                else:
                    messages.warning(
                        self.request, "You have not added a billing address")
                    return redirect("core:checkout")
            else:
                return redirect("core:home")
        except Exception as e:
            print("=== error occured while getting stripe")
            print(e)
            traceback.format_exc(e)
            return redirect("core:checkout")
            

    def post(self, *args, **kwargs):
        kind = self.request.session.get('kind', 0)
        order = get_user_pending_order(self.request)
        form = PaymentForm(self.request.POST)
        userprofile, created = UserProfile.objects.get_or_create(user=self.request.user)
        charge = None
        braintree_id = None

        if form.is_valid():
            stripe_token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')
            amount = int(order.get_total())
            try:
                if stripe_token:
                    if save:
                        if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                            customer = stripe.Customer.retrieve(
                                userprofile.stripe_customer_id)
                            temp = customer.sources.create(source=stripe_token)
                            stripe.Customer.modify(
                                userprofile.stripe_customer_id,
                                default_source=temp.id
                            )
                        else:
                            customer = stripe.Customer.create(
                                email=self.request.user.email,
                            )
                            customer.sources.create(source=stripe_token)
                            userprofile.stripe_customer_id = customer['id']
                            userprofile.one_click_purchasing = True
                            userprofile.save()
                    else:
                        charge = stripe.Charge.create(
                            amount=amount * 100,
                            currency='usd',
                            source=stripe_token,
                        )

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount * 100,  # cents
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )

            except error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Payment not processed! Not authenticated")
                return redirect("core:home")

            except error.StripeError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("core:home")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                messages.warning(self.request, "Payment not processed! Invalid parameters")
                return redirect("core:home")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("core:home")

            # create the payment
            payment = Payment()
            if charge:
                payment.stripe_charge_id = charge.get('id', '')
                payment.payment_method = 'S'

            if braintree_id:
                payment.braintree_charge_id = braintree_id
                payment.payment_method = 'B'
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to the order

            order_items = order.items.all()
            order_items.update(ordered=True, status='P')
            for item in order_items:
                item.save()

            order.ordered = True
            order.status = 'P'
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()
            History.objects.create(user=order.user, action='Purchased', item_str=order.get_purchased_items(),
                                   reason="Stripe payment done", order_str=order.id)
            # TODO Add giveaway stats
            # try:
            #     GiveawayStats.objects.create(order_id=order.id)
            # except Exception as e:
            #     print(e)
            if order.kind == 0:
                messages.success(self.request,
                                 "Head over to the Launch Pad to start your giveaway! If no one is in line, you will start immediately!",
                                 extra_tags='order_complete')
                # TODO Direct to payment statuses
                return redirect("retweet_picker:giveaway-list")
            else:
                messages.success(self.request, "Payment succeed",
                                 extra_tags='order_complete')
                # TODO Direct to payment statuses
                del_timing(order.user.id, 'stripe payment done')
                return redirect("core:user-orders")
            messages.warning(self.request, "Invalid data received")
        return redirect("core:payment")


class BitpayView(View):
    """
    View dedicated to handling payment for stripe
    """

    def get(self, *args, **kwargs):
        order = get_user_pending_order(self.request)
        if order != 0:
            try:
                tokens = {
                    'pos': settings.BITPAY_TOKEN
                }
                # client = Client(api_uri="https://test.bitpay.com") #if api_uri is not passed, it defaults to "https://bitpay.com"
                if settings.BITPAY_TEST == True:
                    client = Client(api_uri="https://test.bitpay.com", tokens=tokens)
                    amount = 1
                else:
                    client = Client(api_uri="https://bitpay.com", tokens=tokens)
                    amount = int(order.get_total())
                # client.create_token('pos')
                # client.pair_pos_client("faD2tzX")

                host = self.request.get_host()
                notify_url = 'https://{}{}'.format(host, reverse('core:bitpay-notify'))

                pos_data = {
                    "price": amount,
                    "currency": "USD",
                    "token": client.tokens['pos'],
                    'orderId': order.id,
                    'notificationURL': notify_url,
                    'notificationEmail': '',
                    'buyer': {
                        'email': self.request.user.email,
                        'notify': True
                    },
                }
                # invoice = client.create_invoice(pos_data)
                res = client.unsigned_request('/invoices', pos_data)
                if res.ok:
                    res = res.json()
                    invoice_id = res['data']['id']
                    context = {
                        'order': order,
                        'invoice_id': invoice_id,
                        'order_id': order.id,
                        'bitpay_env': 'test' if settings.BITPAY_TEST == True else 'prod'
                    }
                    return render(self.request, "shop_v2/bitpay.html", context)
                else:
                    messages.warning(self.request, "Creating invoice failed. Error:")
                    return redirect("core:checkout")
            except Exception as e:
                logging.info(e)
                messages.warning(self.request, "Creating bitpay invoice failed. Error:" + str(e))
                return redirect("core:checkout")
        else:
            return redirect("core:home")

    def post(self, *args, **kwargs):
        try:
            kind = self.request.session.get('kind', 0)
            order = get_user_pending_order(self.request)
            form = BitpayForm(self.request.POST)
            if form.is_valid() and order != 0:
                invoice_id = form.cleaned_data.get('invoice_id')
                order_id = form.cleaned_data.get('order_id')
                amount = int(order.get_total())
                if str(order.id) == order_id:
                    # create the payment
                    payment = Payment()
                    payment.payment_method = 'C'
                    payment.user = self.request.user
                    payment.amount = order.get_total()
                    payment.save()

                    # assign the payment to the order

                    order_items = order.items.all()
                    order_items.update(ordered=True, status='P')
                    for item in order_items:
                        item.save()

                    order.ordered = True
                    order.status = 'P'
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()
                    History.objects.create(user=order.user, action='Purchased', item_str=order.get_purchased_items(),
                                           reason="Bitcoin payment done", order_str=order.id)
                if order.kind == 0:
                    messages.success(self.request,
                                     "Head over to the Launch Pad to start your giveaway! If no one is in line, you will start immediately!",
                                     extra_tags='order_complete')
                    # TODO Direct to payment statuses
                    return redirect("retweet_picker:giveaway-list")
                else:
                    messages.success(self.request, "Payment succeed",
                                     extra_tags='order_complete')
                    # TODO Direct to payment statuses
                    del_timing(order.user.id, 'bitcoin payment done')
                    return redirect("core:user-orders")
        except Exception as e:
            logging.info(e)
            messages.warning(self.request, "Invalid data received")
        return redirect("core:home")


@csrf_exempt
def bitpay_notify(request):
    try:
        data = json.loads(request.body)
        if data['status'] in ['confirmed', 'complete', 'paid']:
            order_id = data['orderId']
            orders = Order.objects.filter(id=order_id)
            if orders.exists():
                order = orders[0]
                if order.ordered == True:
                    return HttpResponse(status=200)
                payment = Payment()
                payment.payment_method = 'C'
                payment.user = order.user
                payment.amount = order.get_total()
                payment.save()

                order_items = order.items.all()
                order_items.update(ordered=True, status='P')
                for item in order_items:
                    item.save()

                order.ordered = True
                order.status = 'P'
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()
                History.objects.create(user=order.user, action='Purchased', item_str=order.get_purchased_items(),
                                       reason="Bitcoin payment done", order_str=order.id)
    except Exception as e:
        logging.info(e)
    return HttpResponse(status=200)


@method_decorator(account_type_check, name='dispatch')
class HomeView(ListView):
    model = Item
    paginate_by = 12
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        res = removefromcart(self.request)
        if res['removed'] == 1:
            messages.warning(self.request, res['msg'])
        return context


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        bmsg = 0
        try:
            res = removefromcart(self.request)
            if res['removed'] == 1:
                messages.warning(self.request, res['msg'])
                bmsg = 1
            order = Order.objects.get(user=self.request.user, ordered=False, kind=0)
            socials = Item.objects.filter(category='SB')
            context = {
                'object': order,
                'social_boost': socials
            }
            self.request.session['kind'] = 0
            return render(self.request, 'shop_v2/cart.html', context)
        except ObjectDoesNotExist:
            if bmsg == 0:
                messages.warning(self.request, "You do not have an active order")
            return redirect("/shop")


@method_decorator(account_type_check, name='dispatch')
class ItemDetailView(DetailView):
    model = Item
    template_name = "shop_v2/product.html"


@account_type_check
@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False, kind=0)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(kind=0, item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.available_to_run += 1
            order_item.save()
            # messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            # messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, f"{order_item} was added to your cart.")
        return redirect("core:order-summary")


@account_type_check
@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False,
        kind=0
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            if order.coupon:
                order.coupon = None
                order.save()
            messages.info(request, f"{order_item} was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "Item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@account_type_check
@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False,
        kind=0
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.available_to_run -= 1
                order_item.save()
            else:
                if order.coupon:
                    order.coupon = None
                    order.save()
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        if coupon.use_max > 0:
            coupon.use_max -= 1
            coupon.save()
            return coupon
        else:
            messages.error("Coupon invalid or expired!")
            return redirect(request, "core:checkout")
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False, kind=0)
                try:
                    order.coupon = get_coupon(self.request, code)
                    order.save()
                    messages.success(self.request, "Successfully applied coupon")
                    return redirect("core:checkout")
                except:
                    messages.error(self.request, "Coupon does not exist or could not be applied")
                    return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "shop/request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")


@csrf_exempt
def payment_done(request):
    messages.success(request, "Payment complete!")
    context = {}
    try:
        kind = request.session.get('kind', 0)
        user_order = Order.objects.filter(user_id=request.user.id, kind=kind).last()
        context['purchased_items'] = user_order.get_purchased_items()
        context['ref_code'] = user_order.ref_code
        context['total_charged'] = user_order.get_total()
    except Exception as e:
        logging.info(f'Error on payment done page: {e}')
    return render(request, 'shop_v2/done.html', context=context)


@csrf_exempt
def payment_canceled(request):
    return render(request, 'shop_v2/canceled.html')


class PaypalPaymentProcess(View):
    def get(self, request):
        res = removefromcart(self.request)
        if res['removed'] == 1:
            messages.warning(self.request, res['msg'])
            return redirect("core:order-summary")
        # order_id = request.GET['order_id']
        # order = get_object_or_404(Order, id=order_id)
        kind = self.request.session.get('kind', 0)
        order = Order.objects.get(user=self.request.user, ordered=False, kind=kind)
        host = request.get_host()

        if kind == 0:
            return_url = 'http://{}{}'.format(host, reverse('core:done'))
        else:
            return_url = 'http://{}{}'.format(host, reverse('core:user-orders'))
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': order.get_total(),
            'item_name': 'Order {}:{}'.format(order.id, order.get_purchased_items()),
            'invoice': str(order.id) + "_" + str(kind),
            'currency_code': 'USD',
            'notify_url': 'http://{}{}'.format(host, reverse('core:paypal-ipn')),
            'return_url': return_url,
            'cancel_return': 'http://{}{}'.format(host, reverse('core:canceled')),
        }
        form = PayPalPaymentsForm(initial=paypal_dict)
        return render(request, 'shop_v2/process.html', {'order': order,
                                                        'form': form})


@method_decorator(account_type_check, name='dispatch')
class OrderView(View):

    def get(self, *args, **kwargs):
        try:
            orders = Order.objects.filter(user=self.request.user, ordered=True)
            # slot_orders = Order.objects.filter(user=self.request.user, ordered=True, kind=1)
            # TODO Set slot item to 1
            slot_items = OrderItem.objects.filter(user=self.request.user, ordered=True, kind=1)
            context = {
                'orders': orders,
                # 'slot_orders': slot_orders,
                'slot_items': slot_items,
            }

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "shop_v2/orders.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:home")


@method_decorator(account_type_check, name='dispatch')
class AllOrderView(View):

    def get(self, *args, **kwargs):
        try:
            orders = Order.objects.filter(user=self.request.user, ordered=True, kind=1)
            slot_items = OrderItem.objects.filter(ordered=True, kind=1)
            data = []
            for item in slot_items:
                temp = {}
                temp['launch_code'] = item.launch_code
                temp['username'] = item.user.username
                temp['email'] = item.user.email
                temp['slot_user'] = item.username
                temp['title'] = item.slot.title
                temp['points'] = item.quantity * item.slot.points
                temp['amount'] = item.quantity * item.slot.value
                if item.orders.all().count() == 0:
                    temp['order_date'] = ""
                else:
                    temp['order_date'] = item.orders.all()[0].ordered_date
                data.append(temp)
            # sort_data = sorted(data, key = lambda i: (i['launch_code'], i['username'], i['title'], i['slot_user'], i['points']))  
            context = {
                'orders': data,
            }

            return render(self.request, "shop_v2/allorders.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:home")


@method_decorator(account_type_check, name='dispatch')
class AccountView(View):

    def get(self, *args, **kwargs):
        try:
            orders = Order.objects.filter(ordered=True, kind=1)
            accounts = []
            ids = []
            for order in orders:
                if order.items.all().count() == 0:
                    continue
                if order.user.id in ids:
                    continue
                else:
                    ids.append(order.user.id)
                    temp = {}
                    temp['username'] = order.user.username
                    temp['email'] = order.user.email
                    temp['name'] = order.user.first_name + " " + order.user.last_name
                    temp['date'] = order.user.date_joined
                    accounts.append(temp)
            # print(accounts)
            context = {
                'accounts': accounts,
            }
            return render(self.request, "shop_v2/accounts.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "There is not accounts signed up for community")
            return redirect("core:home")


@method_decorator(account_type_check, name='dispatch')
class DisableView(View):

    def get(self, *args, **kwargs):
        try:
            slots = Slotitem.objects.all()
            items = Item.objects.all()
            context = {
                'items': items,
                'slots': slots,
            }

            return render(self.request, "shop_v2/disable.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have Giveaway items")
            return redirect("core:home")


def removefromcart(request):
    res = {'left': 0, 'msg': '', 'removed': 0}
    kind = request.session.get('kind', 0)
    user = request.user
    order_qs = Order.objects.filter(user=user, ordered=False, kind=kind)
    if not order_qs.exists():
        return res
    order = order_qs[0]
    order_items = order.items.filter(kind=kind, item__available=False)
    if len(order_items) > 0:
        res['removed'] = 1
        res['msg'] = "The item in your cart is no longer available and has been removed"
    order_items.delete()
    if len(order.items.all()) == 0:
        order.delete()
    else:
        res['left'] = 1
    return res
