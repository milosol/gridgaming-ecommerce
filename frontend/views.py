from django.shortcuts import render
from allauth.socialaccount.models import SocialAccount
from .forms import UserAccountForm
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


class AdsView(View):
    """Replace pub-0000000000000000 with your own publisher ID"""
    ad_string = "google.com, pub-2399779593674817, DIRECT, f08c47fec0942fa0"
    
    def get(self, request, *args, **kwargs):
        return HttpResponse(self.ad_string)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


# Create your views here.

def index(request):
    return render(request, "core/index.html")


def home(request):
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

@login_required
def profile(request):
    social_account_extras = SocialAccount.objects.get(user=request.user)

    return render(request, "frontend/profile.html")


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
