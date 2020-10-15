from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import reverse
from django.contrib import messages


def account_type_check(function):
    def _function(request,*args, **kwargs):
        if hasattr(request.user, 'account_type'):
            if request.user.account_type is None:
                messages.info(request, "Please select role before using the grid.")
                return HttpResponseRedirect(reverse('frontend:account_type'))
            return function(request, *args, **kwargs)
        # else:
        #     return HttpResponseRedirect(HttpResponse('Error processing request. Please try again!'))
    return _function


def cleared_hot_check(function):
    def _function(request,*args, **kwargs):
        if request.user.cleared_hot is False:
            messages.warning(request, "Must be cleared hot before performing self launch! Admin will manually approve after first sponsor.")
            return HttpResponseRedirect(reverse('retweet_picker:giveaway-list'))
        return function(request, *args, **kwargs)
    return _function