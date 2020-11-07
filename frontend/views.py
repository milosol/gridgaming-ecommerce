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
from core.models import UserProfile, Payment
from core.forms import PaymentForm
from stripe import error
from django.utils import timezone
from datetime import timedelta
from retweet_picker.views import set_donemonth
from .ads import prometric_ads

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class AdsView(View):
    """Replace pub-0000000000000000 with your own publisher ID"""
    #ad_string = "google.com, pub-2399779593674817, DIRECT, f08c47fec0942fa0"
    ad_string = prometric_ads
    
    def get(self, request, *args, **kwargs):
        return HttpResponse(self.ad_string, content_type="text/plain")


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
    for pp in pps:
        temp = {}
        temp['plan'] = pp.plan
        temp['label'] = pp.label
        temp['price'] = pp.price
        temp['limit_times'] = pp.limit_times
        temp['limit_count'] = pp.limit_count
        if pp.plan == membership.plan:
            pp.status = 1
            selected = True
        else:
            pp.status= 0 if selected else 1
        temp['status'] = pp.status
        pp_array.append(temp)
    
    context['plan'] = membership.plan
    context['pricing_plans_set'] = pps
    context['pricing_plans_json'] = dumps(pp_array)
    context['tab'] = tab
    return render(request, "frontend/profile.html", context=context)
    
def pre_checkout(request):
    context = {}
    if request.method == "POST":
        try:
            reason = request.POST.get('reason')
            if reason == 'membership':
                upgradeto = request.POST.get('upgradeto')
                months = request.POST.get('months')
                amount = request.POST.get('amount')
                uo, created = Upgradeorder.objects.get_or_create(user_id=request.user.id, reason=reason, months=months, amount=amount, upgradeto=upgradeto)
            else:
                gwid = request.POST.get('gwid')
                amount = request.POST.get('amount')
                uo, created = Upgradeorder.objects.get_or_create(user_id=request.user.id, reason=reason, gwid=gwid, amount=amount)
            
            request.session['uoid'] = uo.id
            return redirect("frontend:checkout")
        except Exception as e:
            print(e)
            messages.warning(request, "Error occured while pre checkout. Please try again.")
            return redirect("core:home")
    else:
        return redirect("core:home")


class CheckoutView(View):
    def get(self, request):
        
        context = {}
        try:
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
        print("==== payment option : ", method)
        if method == 'paypal':
            return redirect("frontend:paypalpayment")
        else:
            return redirect("frontend:stripepayment")


class PaypalPaymentView(View):
    def get(self, request):
        try: 
            uoid = self.request.session.get('uoid', -1)
            if uoid == -1:
                messages.warning(self.request, "Please try again.")
                return redirect("frontend:checkout")
            
            uo = Upgradeorder.objects.get(id=uoid)
            host = request.get_host()

            if uo.reason == 'membership':
                return_url = 'http://{}{}'.format(host, reverse('frontend:profile')) + "?tab=membership"
                item_name = "Upgrade Membership : " + uo.upgradeto + "_" + str(uo.id)
            else:
                return_url = 'http://{}{}'.format(host, "/contests/" + str(uo.gwid) + "/entries")
                item_name = "Pay for drawing " + str(uo.id)
            print(" === return url :", return_url)
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': uo.amount,
                'item_name': item_name,
                'invoice': "drawormembership_" + str(uo.id),
                'currency_code': 'USD',
                'notify_url': 'http://{}{}'.format(host, reverse('frontend:paypal-ipn')),
                'return_url': return_url,
                'cancel_return': 'http://{}{}'.format(host, reverse('frontend:payment_canceled')),
            }
            form = PayPalPaymentsForm(initial=paypal_dict)
            return render(request, 'frontend/paypalprocess.html', {'order': uo,
                                                            'form': form})
        except Exception as e:
            print(e)
            messages.warning(self.request, "Please try again.")
            return redirect("frontend:checkout")

@csrf_exempt
def payment_canceled(request):
    return render(request, 'frontend/canceled.html')


class StripePaymentView(View):

    def get(self, *args, **kwargs):
        try:
            uoid = self.request.session.get('uoid', -1)
            uo = Upgradeorder.objects.get(id=uoid)
            context = {
                'order': uo,
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
            messages.warning(self.request, "There is no pay order. Please try again.")
            return redirect("frontend:checkout")
            
    def post(self, *args, **kwargs):
        try:
            
            form = PaymentForm(self.request.POST)
            uoid = self.request.session.get('uoid', -1)
            uo = Upgradeorder.objects.get(id=uoid)
            userprofile, created = UserProfile.objects.get_or_create(user=self.request.user)
            charge = None
            if form.is_valid():
                stripe_token = form.cleaned_data.get('stripeToken')
                save = form.cleaned_data.get('save')
                use_default = form.cleaned_data.get('use_default')
                amount = uo.amount
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
                    messages.warning(self.request, "Payment not processed! Not authenticated")
                    return redirect("frontend:checkout")

                except error.StripeError as e:
                    body = e.json_body
                    err = body.get('error', {})
                    messages.warning(self.request, f"{err.get('message')}")
                    return redirect("frontend:checkout")

                except stripe.error.InvalidRequestError as e:
                    # Invalid parameters were supplied to Stripe's API
                    messages.warning(self.request, "Payment not processed! Invalid parameters")
                    return redirect("frontend:checkout")

                except Exception as e:
                    messages.warning(self.request, "A serious error occurred. We have been notifed.")
                    return redirect("frontend:checkout")

                payment = Payment()
                if charge:
                    payment.stripe_charge_id = charge.get('id', '')
                    payment.payment_method = 'S'

                payment.user = self.request.user
                payment.amount = amount
                payment.save()

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
                    
                    messages.success(self.request,
                                    "Your membership is upgraded!", extra_tags='order_complete')
                    return redirect("/profile?tab=membership")
                else:
                    add_drawcount(uo.id)
                    messages.success(self.request, "Payment succeed", extra_tags='order_complete')
                    return redirect("/contests/" + str(uo.gwid) + "/entries")
                
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
        membership, created = Membership.objects.get_or_create(user_id=request.user.id)
        if membership.plan != 'F':
            if membership.end_time < timezone.now():
                membership.plan = 'F'
                membership.paid_month = 0
                membership.done_count = 0
                membership.done_month = 0
                membership.save()
            else:
                set_donemonth(membership.id)
                membership = Membership.objects.get(user_id=request.user.id)
                res['membership'] = PricingPlan.objects.filter(plan=membership.plan).first().label
    except Exception as e:
        print(e)
        res['success'] = False
        res['membership'] = 'Free'
        res['msg'] = 'Error occured while getting membership'
    return JsonResponse(res)

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