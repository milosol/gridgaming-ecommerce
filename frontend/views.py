from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
from django.shortcuts import render
from allauth.socialaccount.models import SocialAccount
from .forms import UserAccountForm
from django.http import JsonResponse
from users.models import UserRoles, User
from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaulttags import register
from .utils import build_socials
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views import View
import math
import random
import string
import stripe
from json import dumps
from django.conf import settings
from retweet_picker.models import PricingPlan, Membership, PRICINGPLAN_CHOICES, Upgradeorder, DrawPrice, GiveawayWinners
from paypal.standard.forms import PayPalPaymentsForm
from django.views.decorators.csrf import csrf_exempt
from core.models import UserProfile, Payment, History
from core.forms import PaymentForm, CoinbaseForm
from stripe import error
from django.utils import timezone
from datetime import timedelta
from coinbase_commerce.client import Client
from .models import BuyCredit
from .utils import *
from frontend.utils import get_ads
coinbase_api_key = settings.COINBASE_API_KEY
client = Client(api_key=coinbase_api_key)


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class AdsView(View):
    """Replace pub-0000000000000000 with your own publisher ID"""
    #ad_string = "google.com, pub-2399779593674817, DIRECT, f08c47fec0942fa0"
    ad_string = get_ads()
    
    def get(self, request, *args, **kwargs):
        ad_string = get_ads()
        return HttpResponse(ad_string, content_type="text/plain")


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


# Create your views here.

def index(request):
    return render(request, "core/index.html")


def home(request):
    if request.user.is_authenticated:
        messages.success(request, f'Welcome back, {request.user.username}!')
        return redirect('core:home')
    else:
        return render(request, "frontend/index.html")


class ProfileHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'frontend/profile.html'
    user_check_failure_path = reverse_lazy("account_signup")
    success_url = reverse_lazy("profile")

    def check_user(self, user):
        if user.is_active:
            return True
        return False

    def record_create(self, service, username):
        return {'service_name': service, 'service_nick': username}

        # Make final check for epic and if still in list query yunite with discord ID

    def get_context_data(self, **kwargs):
        context = super(ProfileHomeView, self).get_context_data(**kwargs)
        # profile = UserProfile.objects.get_or_create(user=self.request.user)[0]
        # context['profile'] = profile
        context['socials'] = build_socials(self.request.user.id)
        return context

#@login_required
def profile(request):
    # social_account_extras = SocialAccount.objects.get(user=request.user)
    tab = request.GET.get('tab', 'home')
    request.session['uoid'] = -1
    context = {}
    membership, created = Membership.objects.get_or_create(user_id=request.user.id)
    if PricingPlan.objects.all().count() == 0:
        for choice, label in PRICINGPLAN_CHOICES:
            PricingPlan.objects.create(plan=choice, label=label)
    pps = PricingPlan.objects.filter(plan=membership.plan)
    if pps.exists():
        if pps[0].unlimited_times == True:
            context['left_label'] = 'unlimited'
        else:
            context['left_label'] = str(pps[0].limit_times - membership.done_count + membership.bonus_count) + " / " + str(pps[0].limit_times)
    else:
        context['left_label'] = '0'
    context['left_label'] += ' this month'
    if membership.plan == 'F':
        context['minus_price'] = 0
    else:
        try:
            diff = membership.end_time - timezone.now()
            diff_month = diff.total_seconds()/(3600*24*30)
            current_price = PricingPlan.objects.filter(plan=membership.plan).first().price
            context['minus_price'] = math.floor(diff_month * current_price)
        except Exception as e:
            print(e)
            context['minus_price'] = 0
            
    pps = PricingPlan.objects.all()
    pp_array = []
    selected = False
    cc_per_usd = get_cc_per_usd()
    for pp in pps:
        pp.price_credit = pp.price * cc_per_usd
        temp = {}
        temp['plan'] = pp.plan
        temp['label'] = pp.label
        temp['price'] = pp.price
        temp['price_credit'] = pp.price_credit
        temp['limit_times'] = pp.limit_times
        temp['limit_count'] = pp.limit_count
        if pp.plan == membership.plan:
            pp.status = 1
            selected = True
        else:
            pp.status= 0 if selected else 1
        temp['status'] = pp.status
        pp_array.append(temp)
    
    context['cc_per_usd'] = cc_per_usd
    context['current_credit'] = get_credit_amount(request.user.id)
    context['plan'] = membership.plan
    context['pricing_plans_set'] = pps
    context['pricing_plans_json'] = dumps(pp_array)
    context['tab'] = tab
    return render(request, "frontend/profile.html", context=context)
    
def pre_checkout(request):
    context = {}
    if request.method == "POST":
        try:
            upgradeto = request.POST.get('upgradeto')
            months = int(request.POST.get('months'))
            amount = int(request.POST.get('amount'))
            current_credit = get_credit_amount(request.user.id)
            cc_per_usd = get_cc_per_usd()
            if current_credit >= amount * cc_per_usd:
                membership, created = Membership.objects.get_or_create(user_id=request.user.id)
                membership.plan = upgradeto
                membership.paid_month = months
                membership.paid_time = timezone.now()
                membership.analyzed_time = timezone.now()
                membership.end_time = membership.paid_time + timedelta(days=months*30)
                membership.done_count = 0
                membership.done_month = 0
                membership.freecredit_donemonth = 0
                membership.ended_alert = 0
                membership.save()
                add_free_credit(request.user.id)
                credit_minus(request.user.id, amount*cc_per_usd)
            else:
                messages.warning(request, "You have not enough credits. Buy credit and try again.")
            # uo, created = Upgradeorder.objects.get_or_create(user_id=request.user.id, reason=reason, months=months, amount=amount, upgradeto=upgradeto, payment_status='W')
        except Exception as e:
            print(e)
            messages.warning(request, "Error occured while upgrading membership. Please try again.")
        return redirect("/profile?tab=membership")
    else:
        return redirect("/profile?tab=membership")


class CheckoutView(View):
    def get(self, request):
        try:
            context = {} 
            kind = request.GET.get('kind', '')
            uoid = self.request.session.get('uoid', -1)
            print(" == checkout page ", uoid)
            uo = Upgradeorder.objects.get(id=uoid)
            context['uo'] = uo
            return render(request, 'frontend/checkout.html', context=context)
        except Exception as e:  
            print(e)
            messages.warning(request, "Error occured while checkout. Please try again.")
            return redirect("core:home")
        
    def post(self, request):
        method = request.POST.get('payment_option')
        if method == 'paypal':
            return redirect("frontend:paypalpayment")
        elif method == 'stripe':
            return redirect("frontend:stripepayment")
        else:
            return redirect("frontend:coinbasepayment")

def bought_credit(bcid):
    try:
        bc = BuyCredit.objects.get(id=bcid)
        if bc.added_credit == False:
            membership = Membership.objects.get(user_id=bc.user.id)
            membership.credit_amount += bc.credit_amount
            membership.save()
            bc.added_credit = True
            bc.save()
    except Exception as e:
        print(e)
    
class PaypalPaymentView(View):
    def get(self, request):
        try: 
            bcid = self.request.session.get('bcid', -1)
            if bcid < 0:
                messages.warning(self.request, "Error occured. Please try again")
                return redirect("frontend:credits")
            bc = BuyCredit.objects.get(id=bcid)
            host = request.get_host()

            # if uo.reason == 'membership':
            #     return_url = 'http://{}{}'.format(host, reverse('frontend:profile')) + "?tab=membership"
            #     item_name = "Upgrade Membership : " + uo.upgradeto + "_" + str(uo.id)
            # else:
            #     return_url = 'http://{}{}'.format(host, "/retweet-picker/draw/" + str(uo.gwid))
            #     item_name = "Pay for drawing " + str(uo.id)
                
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': bc.usd_pay,
                'item_name': "Buy Credit",
                'invoice': "buy_credit_" + str(bc.id),
                'currency_code': 'USD',
                'notify_url': 'http://{}{}'.format(host, reverse('frontend:paypal-ipn')),
                'return_url': 'http://{}{}'.format(host, reverse('frontend:payment_done')),
                'cancel_return': 'http://{}{}'.format(host, reverse('frontend:payment_canceled')),
            }
            form = PayPalPaymentsForm(initial=paypal_dict)
            return render(request, 'frontend/paypalprocess.html', {'order': bc,
                                                            'form': form})
        except Exception as e:
            print(e)
            messages.warning(self.request, "Please try again.")
            return redirect("frontend:checkout")

@csrf_exempt
def payment_canceled(request):
    return render(request, 'frontend/canceled.html')


@csrf_exempt
def payment_done(request):
    cart_param = request.GET.get('cart', 'credit')
    context = {'cart_param': cart_param}
    return render(request, 'frontend/done.html', context)



class CoinbasePaymentView(View):
    """
    View dedicated to handling payment for coinbase
    """

    def get(self, request):
        try: 
            bcid = self.request.session.get('bcid', -1)
            if bcid < 0:
                messages.warning(self.request, "Error occured. Please try again")
                return redirect("frontend:credits")
            
            cart_param = self.request.GET.get('cart', 'credit')
            bc = BuyCredit.objects.get(id=bcid)
            host = request.get_host()
            # return_url = 'http://{}{}'.format(host, reverse('frontend:payment_done')) + '?cart=' + cart_param
            description = 'Buy Credit [' + bc.user.username + ' : ' + str(bc.credit_amount) + ' credits]'  
            order_name = 'buy_credit_' + str(bc.id)
            checkout_info = {
                "name": order_name,
                "description": description,
                "pricing_type": 'fixed_price',
                "local_price": {
                    "amount": bc.usd_amount,
                    "currency": "USD"
                },
                "requested_info": []
            }
            # checkouts = client.checkout.list()
            # for checkout in client.checkout.list_paging_iter():
            #     if order_name == checkout.name:
            #         checkout.delete()
                    
            checkout = client.checkout.create(**checkout_info)
            print("====== checkout created :", checkout.id, " - ", bc.id)
            context = {
                'order': bc,
                'checkout_id': checkout.id,
                'order_id': bc.id,
                'cart_param': cart_param
            }
            return render(self.request, "frontend/coinbase.html", context)
        except Exception as e:
            print(e)
            messages.warning(self.request, "Creating coinbase checkout failed. Error:" + str(e))
            return redirect("frontend:credits")

    def post(self, *args, **kwargs):
        try:
            print("=== coinbase post")
            form = CoinbaseForm(self.request.POST)
            if form.is_valid():
                checkout_id = form.cleaned_data.get('checkout_id')
                order_id = form.cleaned_data.get('order_id')
                cart_param = form.cleaned_data.get('cart_param')
                bc = BuyCredit.objects.get(id=order_id)
                print("=== bc. payment status :", bc.payment_status)
                if bc.payment_status != 'C':
                    print("=== created payment")
                    # create the payment
                    payment = Payment()
                    payment.payment_method = 'C'
                    payment.user = self.request.user
                    payment.amount = bc.usd_amount
                    payment.credit_amount = bc.credit_amount
                    payment.save()
                    bc.payment = payment
                    bc.payment_status = 'C'
                    bc.save()
                    bought_credit(bc.id)
                    # return redirect("frontend:payment_done")
                    return redirect(reverse("frontend:payment_done")+ '?cart=' + cart_param)
                    # set_upgradeorder_paid(uo.id, payment)
                    
                # if uo.reason == 'membership':
                #     messages.success(self.request,
                #                     "Your membership is upgraded!", extra_tags='order_complete')
                #     return redirect("/profile?tab=membership")
                # else:
                #     messages.success(self.request, "Payment succeed", extra_tags='order_complete')
                #     return redirect("/retweet-picker/" + str(uo.gwid) + "/entries")
            
        except Exception as e:
            print(e)
            messages.warning(self.request, "Invalid data received")
        return redirect("core:home")

def set_upgradeorder_paid(uoid, payment):
    uo = Upgradeorder.objects.get(id=uoid)
    uo.payment = payment
    uo.payment_status = 'C'
    uo.save()
    if uo.reason == 'membership':
        membership = get_object_or_404(Membership, user_id=uo.user_id)
        membership.plan = uo.upgradeto
        membership.paid_month = uo.months
        membership.paid_time = timezone.now()
        membership.end_time = membership.paid_time + timedelta(days=uo.months*30)
        membership.done_count = 0
        membership.done_month = 0
        membership.save()
    else:
        add_drawcount(uo.id)

class StripePaymentView(View):

    def get(self, *args, **kwargs):
        try:
            cart_param = self.request.GET.get('cart', 'credit')
            bcid = self.request.session.get('bcid', -1)
            if bcid < 0:
                messages.warning(self.request, "Error occured. Please try again")
                return redirect("frontend:credits")
            
            bc = BuyCredit.objects.get(id=bcid)
            
            context = {
                'order': bc,
                'cart_param': cart_param,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
                # 'client_token': client_token,
                'client_token': create_ref_code(),
            }
            userprofile, created = UserProfile.objects.get_or_create(user=self.request.user)
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
            return render(self.request, "frontend/stripe.html", context)
        except Exception as e:
            print(e)
            messages.warning(self.request, "Please try again.")
            return redirect("frontend:credits")
            
    def post(self, *args, **kwargs):
        try:
            
            bcid = self.request.session.get('bcid', -1)
            # cart_param = self.request.session.get('cart', 'credit')
            bc = BuyCredit.objects.get(id=bcid)
            form = PaymentForm(self.request.POST)
            userprofile, created = UserProfile.objects.get_or_create(user=self.request.user)
            charge = None
            if form.is_valid():
                stripe_token = form.cleaned_data.get('stripeToken')
                save = form.cleaned_data.get('save')
                use_default = form.cleaned_data.get('use_default')
                cart_param = form.cleaned_data.get('cart_param')
                amount = bc.usd_amount
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
                                amount=int(amount * 100),
                                currency='usd',
                                source=stripe_token,
                            )
                            
                    if use_default or save:
                        # charge the customer because we cannot charge the token more than once
                        charge = stripe.Charge.create(
                            amount=int(amount * 100),  # cents
                            currency="usd",
                            customer=userprofile.stripe_customer_id
                        )

                except error.AuthenticationError as e:
                    messages.warning(self.request, "Payment not processed! Not authenticated")
                    return redirect("frontend:credits")

                except error.StripeError as e:
                    body = e.json_body
                    err = body.get('error', {})
                    messages.warning(self.request, f"{err.get('message')}")
                    return redirect("frontend:credits")

                except stripe.error.InvalidRequestError as e:
                    # Invalid parameters were supplied to Stripe's API
                    messages.warning(self.request, "Payment not processed! Invalid parameters")
                    return redirect("frontend:credits")

                except Exception as e:
                    messages.warning(self.request, "A serious error occurred. We have been notifed.")
                    return redirect("frontend:credits")

                payment = Payment()
                if charge:
                    payment.stripe_charge_id = charge.get('id', '')
                    payment.payment_method = 'S'

                payment.user = self.request.user
                payment.amount = amount
                payment.credit_amount = bc.credit_amount
                payment.save()
                bc.payment = payment
                bc.payment_status = 'C'
                bc.save()
                bought_credit(bc.id)
                History.objects.create(user=bc.user, action='Buy Credit', item_str=str(bc.credit_amount) + ' credits',
                                            reason="Stripe payment done", order_str=bc.id)
                return redirect(reverse("frontend:payment_done")+ '?cart=' + cart_param)
                # if uo.reason == 'membership':
                #     messages.success(self.request,
                #                     "Your membership is upgraded!", extra_tags='order_complete')
                #     return redirect("/profile?tab=membership")
                # else:
                #     messages.success(self.request, "Payment succeed", extra_tags='order_complete')
                #     return redirect("/retweet-picker/" + str(uo.gwid) + "/entries")
                
            messages.warning(self.request, "Invalid data received")
            return redirect("frontend:stripepayment")
        except Exception as e:
            print(e)
            messages.warning(self.request, "Error occured. Please try again.")
            return redirect("frontend:stripepayment")
            
def add_drawcount(uoid):
    try:
        uo = Upgradeorder.objects.get(id=uoid)
        dp = DrawPrice.objects.all().first()
        
        count = math.ceil(uo.amount / dp.price * dp.per_amount)
        gw = GiveawayWinners.objects.get(id=uo.gwid)
        gw.paid_count = gw.paid_count + count
        gw.save()
    except Exception as e:
        print(e)

def account_type(request):
    COLOR_CHOICES = ['lime', 'cyan', 'light-green', 'pink', 'amber']
    context = {}
    context['color_choices'] = COLOR_CHOICES
    if request.method == "POST":
        form = UserAccountForm(request.POST)
        if form.is_valid():
            role = get_object_or_404(UserRoles, role_name=form.cleaned_data['user_roles'])
            request.user.account_type = role
            request.user.save()
            messages.success(request, "All set! Welcome to the Grid.")
            return HttpResponseRedirect(reverse('core:home'))
        else:
            print(form.errors)
    else:
        form = UserAccountForm()
    context['form'] = form
    return render(request, "account/account_type.html", context=context)


@csrf_exempt
def get_membership(request):
    res = {'success': True, 'msg': '', 'membership': 'Free'}
    try:
        if PricingPlan.objects.all().count() == 0:
            for choice, label in PRICINGPLAN_CHOICES:
                PricingPlan.objects.create(plan=choice, label=label)
        membership = user_membership(request.user.id)
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        res['credit_count'] = membership.credit_amount
        last_month = timezone.now() - timedelta(days=30)
        if membership.analyzed_time < last_month:
            print("=== set_donemonth when get membership : ", request.user.id)
            set_donemonth(membership.id)
            
        add_free_credit(request.user.id)
        membership = Membership.objects.get(user_id=request.user.id)
        res['membership'] = PricingPlan.objects.filter(plan=membership.plan).first().label
        res['ended_alert'] = membership.ended_alert
        res['freecredit_alert'] = membership.freecredit_alert
        if membership.freecredit_alert > 0:
            res['added_count'] = get_freecredit_amount(request.user.id)
    except Exception as e:
        print(e)
        res['success'] = False
        res['membership'] = 'Free'
        res['credit_count'] = 0
        res['msg'] = 'Error occured while getting membership'
    return JsonResponse(res)


@csrf_exempt
def set_membership_alert(request):
    res = {'success': True, 'msg': ''}
    try:
        membership = user_membership(request.user.id)
        kind = request.POST.get('kind')
        if kind == '0':
            membership.ended_alert = 0
        else:
            membership.freecredit_alert = 0
        membership.save()
    except Exception as e:
        print(e)
        res['success'] = False
    return JsonResponse(res)


class CreditView(View):
    def get(self, request):
        request.session['bcid'] = -1
        need_param = request.GET.get('need', '')
        cart_param = request.GET.get('cart', '')
        context = {}
        cc_per_usd = get_cc_per_usd()
        credit_amount = get_credit_amount(request.user.id)
        min_price = get_min_buy_credit()
        context = {
            'cc_per_usd' : cc_per_usd,
            'min_price': min_price,
            'credit_amount' : credit_amount,
            'need_param' : need_param,
            'cart_param' : cart_param
        }
        return render(request, 'frontend/credits.html', context=context)
        
    def post(self, request):
        cart_param = request.POST.get('cart_param')
        credit_amount = int(request.POST.get('in_credit'))
        if cart_param == '':
            cart_param = 'credit'
        if credit_amount <= 0:
            messages.warning(self.request, "Please input correct credit amount")
            return redirect("frontend:credits")
        usd_pay = credit2usd(credit_amount)
        bc = BuyCredit.objects.create(user=self.request.user, credit_amount=credit_amount, usd_amount=usd_pay)
        request.session['bcid'] = bc.id
        
        method = request.POST.get('payment_option')
        if method == 'paypal':
            return redirect("frontend:paypalpayment")
        elif method == 'stripe':
            return redirect(reverse('frontend:stripepayment') + '?cart=' + cart_param)
            # return redirect("frontend:stripepayment")
        else:
            return redirect(reverse("frontend:coinbasepayment") + '?cart=' + cart_param)


def update_account_type(request):
    if request.method == "POST":
        print(request.name)

    # if request.method == "POST":
    #     form = UserAccountForm(request.POST)
    #     if form.is_valid():
    #         account = form.save(commit=False)
    #         account.user = request.user
    #         account.save()
    #         messages.success(request, "You're all set! Enjoy!")
    #         return redirect('core:home')
    #
    # else:
    #     form = UserAccountForm(initial={0:0})

# @receiver(pre_social_login)
# def handleDuplicateEmail(sender, request, sociallogin, **kwargs):
#     if sociallogin.account.provider == 'facebook' or sociallogin.account.provider == 'twitter':
#         email_address = sociallogin.account.extra_data['email'] # get email address from fb or twitter social account.
#     else:
#         email_address = sociallogin.account.extra_data['email-address']  # Get email from linkedin social account.
#     users = User.objects.all().filter(email=email_address) # This line is problematic
#     if users.exists():
#         user = users.first()
#         if not (user.profile.provider == sociallogin.account.provider):    # Different user is trying to login with already existing user's email address.
#             response = 'Your social account email address is already registered to some account. Please choose a different one.'
#             raise ImmediateHttpResponse(render(request, 'index.html', {'type': True, 'response': response}))