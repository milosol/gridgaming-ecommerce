import logging
import sys

from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.generic import ListView

from core.models import Order, OrderItem
# from retweet_picker.manager import GiveawayManager
from .tasks import start_giveaway_bg, retrieve_tweets_choose_winner_job
from .forms import RetweetChooserForm
from .models import GiveawayResults, TwitterGiveawayID, TwitterGiveaway, GiveawayStats
from .process import ProcessRetrievedTweets
from core.decorators import account_type_check, cleared_hot_check
from django.utils.decorators import method_decorator
from django.http import JsonResponse

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

import time
from datetime import datetime
import django_rq


def new_retweet_contest(request):
    """ Created to pull down results via URL"""
    form = RetweetChooserForm(request.POST or None)
    winner = None
    status = None
    if form.is_valid():
        # Get data from form
        data = form.cleaned_data

        # Use IOC Enrichment on the field
        process_tweets = ProcessRetrievedTweets(tweet_url=data['tweet_url'])
        logging.info('running pipeline')
        process_tweets.run_pipeline()  # Maybe pass request here?
        participant_count = len(process_tweets.participants)
        logging.info('tweets ready')

        # winner = GiveawayInteract.process_giveaway(url=data['tweet_url'],
        #                                                winner_count=data['winner_count'],
        #                                                members_to_follow=data['members_to_follow'],
        #                                                contest_name=data['contest_name'])
        # if winner:
        #    messages.success(request, "Giveaway Successfully processed!")

        # form.save()
        tweet_url = data.get('tweet_url')
        form = RetweetChooserForm()
    else:
        messages.error(request, 'Form is invalid! Please correct and resubmit.')

    latest_winners = GiveawayResults.objects.all()

    try:
        for w in latest_winners:
            w.tweet_url = TwitterGiveawayID.objects.get(pk=w.giveaway_id_id).tweet_url
    except TwitterGiveawayID.DoesNotExist:
        latest_winners = None

    context = {
        'latest_winners': latest_winners,
        # 'tweet_url': tweet_url,
        'form': form,
        'status': status,
        'winner': winner
    }

    return render(request, "api/retweet_picker_create.html", context)


# class GiveawayResultsListView(ListView):
#     template_name = "giveawayresults_list.html"
#     queryset = GiveawayResults.objects.all()


def order_items_prefetch_related_efficient(user_id):
    queryset = Order.objects.filter(ordered=True, user=user_id).prefetch_related(Prefetch("items",
                                                                                          queryset=OrderItem.
                                                                                          objects.select_related(
                                                                                              "item"),
                                                                                          to_attr='ordered_items'
                                                                                          ))

    order_items = []
    for order in queryset:
        item_list = [order_item for order_item in order.ordered_items]
        order_items.append({'order': order,
                            'items': item_list})

    return order_items


def decrease_available_giveaways(order_id):
    # TODO Prompt with modal Are you sure?
    current_item = OrderItem.objects.get(id=order_id)
    if current_item.available_to_run < 1:
        return {'error': 'No more available to run!'}
    else:
        current_item.decrease_available()
        current_item.save()
        logging.info('Order reduced by 1')
    return {'success': "Order successfully processed"}


def sleep_test(time_to_sleep):
    print(f'sleeping in {time_to_sleep} seconds but not pausing execution')
    time.sleep(time_to_sleep)


def queue_giveaway_test(instance, duration):
    instance.test_method(duration)



@cleared_hot_check
def retrieve_tweets_choose_winner(request, existing_tweet_url):
    context = {}
    try:
        retrieve_tweets_choose_winner_job.delay(existing_tweet_url=existing_tweet_url,
                                                user_id=request.user.id)



    except Exception as e:
        messages.error(request, "Your giveaway could not be launched!")
        print(f"ERROR: {e}")
    #return redirect("retweet_picker:giveaway-list")
    return render(request, template_name='launch.html', context=context)

@cleared_hot_check
def launch_giveaway(request, order_id, item_id):
    context = {}
    try:
        order_item = OrderItem.objects.get(id=item_id)
        if request.user.username == 'GridGamingIO':
            sponsors = ['@GridGamingIO']
        else:
            sponsors = ['@GridGamingIO', '@' + request.user.username]
        run_time = int(order_item.item.duration_to_run * request.user.account_type.time_quantifier)
        start_giveaway_bg.delay(user_id=request.user.id,
                                order_id=order_id,
                                sponsors=sponsors,
                                giveaway_amount=int(order_item.item.giveaway_value),
                                duration=run_time)

        status = decrease_available_giveaways(item_id)
        if 'error' not in status:
            queue = django_rq.get_queue('default')
            position_in_queue = len(queue.get_job_ids())
            if position_in_queue:
                messages.success(request, f"Your giveaway is in queue. Current position: {position_in_queue}")
            else:
                messages.success(request, f"Your giveaway is live!")
            # TODO Create queueing system and let user know what position they are in
            redirect("retweet_picker:giveaway-list")
            #return redirect(request.path)
        else:
            messages.error(request, "This order has already been redeemed.")

    except Exception as e:
        messages.error(request, "Your giveaway could not be launched!")
        print(f"ERROR: {e}")
    #return redirect("retweet_picker:giveaway-list")
    return render(request, template_name='launch.html', context=context)


def prelaunch_validator(request, order_id, item_id):
    queryset = Order.objects.filter(ordered=True,
                                    id=request.user.id).prefetch_related(Prefetch("items", queryset=OrderItem.
                                                                                  objects.filter(
        item_id=item_id).select_related(
        "item"),
                                                                                  to_attr='ordered_items'
                                                                                  ))
    for order in queryset:
        for order_item in order.ordered_items:
            if order_item.available_to_run > 0:
                launch_giveaway(request, order_id, item_id)
            else:
                messages.error(request,
                               "This package is no longer available! If this is an error contact support. business@gridgaming.io")
                redirect("retweet_picker:giveaway-list")


def order_details(request, order_id):
    context = {}
    try:
        context['order'] = Order.objects.get(id=order_id)
    except Exception as e:
        print(e)
    return render(request, template_name='order_details.html', context=context)


@method_decorator(account_type_check, name='dispatch')
class OrdersListView(ListView):
    template_name = "command_center.html"
    model = Order

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['order_items'] = order_items_prefetch_related_efficient(self.request.user.id)
        return context


def decoder_ring(request, secret_code):
    winner = False
    msg = {}
    if secret_code == '87a1ad46c7966ce22835ff36fb44a5e5b818009c':
        winner = True
        msg = 'Happiness is... blowing bubbles!'
    data = {
        'winner': winner,
        'msg': msg
    }
    return JsonResponse(data)


def bubble_rescue(request):
    context = {}
    return render(request, "decoder_ring.html", context)

def contest_results(request, order_id):
    """ Take UUID from contest, retrieve the results and present winner. Also have access to reroll when needed"""
    """ Choose winner will execute """
    context = {}
    giveaway_ids = [str(x.giveaway_id.giveaway_id) for x in GiveawayStats.objects.filter(order_id=order_id)]
    giveaway_objs = TwitterGiveawayID.objects.filter(giveaway_id__in=giveaway_ids)
    try:
        giveaway_details = TwitterGiveaway.objects.get(giveaway_id=giveaway_objs)
        context['giveaway_details'] = giveaway_details
    except Exception as e:
        pass

    giveaway_results = GiveawayResults.objects.filter(giveaway_id__in=[x.id for x in giveaway_objs])
    context['giveaway_results'] = giveaway_results

    print(giveaway_ids)

    return render(request, "contest_results.html", context)

# def get_ipaddress(request):
#     # if this is a POST request we need to process the form data
#     if request.method == 'POST':
#         # create a form instance and populate it with data from the request:
#         form = IPAddressForm(request.POST)
#         # check whether it's valid:
#         if form.is_valid():
#             # process the data in form.cleaned_data as required
#             # ...
#             # redirect to a new URL:
#             pass
#             #return HttpResponseRedirect('/thanks/')
#
#     # if a GET (or any other method) we'll create a blank form
#     else:
#         form = IPAddressForm()
#
#     return render(request, 'api/domain.html', {'form': form})
