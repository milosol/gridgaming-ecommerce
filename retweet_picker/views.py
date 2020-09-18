import logging
import sys
import threading
from datetime import timedelta
from django.utils import timezone

from django.contrib import messages
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt

from core.decorators import account_type_check, cleared_hot_check
from core.models import Order, OrderItem
from .forms import RetweetChooserForm
from .models import GiveawayResults, TwitterGiveawayID, TwitterGiveaway, GiveawayStats, GiveawayQueue
from .process import ProcessRetrievedTweets
from .tasks import start_giveaway_bg, retrieve_tweets_choose_winner_job, draw_winner
from users.models import User

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

import time
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
    queryset = Order.objects.filter(ordered=True, user=user_id, kind=0).prefetch_related(Prefetch("items",
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
    # return redirect("retweet_picker:giveaway-list")
    return render(request, template_name='launch.html', context=context)


def queue_launch(queue_id):
    try:
        row = GiveawayQueue.objects.get(id=queue_id)
        if row.status == 'L':
            return False
        row.status = 'L'
        row.save()
        user = User.objects.get(id=row.user_id)
        if user.username == 'GridGamingIO':
            sponsors = ['@GridGamingIO']
        else:
            sponsors = ['@GridGamingIO', '@' + user.username]
        order_item = OrderItem.objects.get(id=row.item_id)
        tweet_url = start_giveaway_bg(user_id=row.user_id,
                                      order_id=row.item_id,
                                      sponsors=sponsors,
                                      giveaway_amount=row.giveaway_amount,
                                      duration=row.duration)

        row.start_time = timezone.now()
        row.tweet_url = tweet_url
        row.save()
        return True
    except Exception as e:
        print(e)
        return False


def queue_retrieve(queue_id):
    try:
        row = GiveawayQueue.objects.get(id=queue_id)
        if row.status == 'R':
             return False
        row.status = 'R'
        row.save()
        print("======== retrieving:", queue_id, ":", row.queue_type, ":", row.tweet_url, )
        
        if row.queue_type == 'H':
            queue = django_rq.get_queue('high')
        elif row.queue_type == 'L':
            queue = django_rq.get_queue('low')
        else:
            queue = django_rq.get_queue('default')
            
        user = User.objects.get(id=row.user_id)
        if user.username == 'GridGamingIO':
            sponsors = ['@GridGamingIO']
        else:
            sponsors = ['@GridGamingIO', '@' + user.username]
        print("======== sponsors : ", sponsors)    
        queue.enqueue(retrieve_tweets_choose_winner_job, existing_tweet_url=row.tweet_url, user_id=row.user_id,
                      order_id=row.item_id, giveaway_amount=row.giveaway_amount, sponsors=sponsors)
        
        # retrieve_tweets_choose_winner_job(existing_tweet_url=row.tweet_url, user_id=row.user_id, order_id=row.item_id, giveaway_amount=row.giveaway_amount, sponsors=sponsors)
        return True
    except Exception as e:
        print(e)
        return False


def process_queue(queue_type):
    try:
        rows = GiveawayQueue.objects.filter(queue_type=queue_type, status='L')
        if rows.exists():
            row = rows[0]
            if row.start_time is not None:
                end_time = row.start_time + timedelta(minutes=row.duration)
                if end_time < timezone.now():
                    queue_retrieve(row.id)
        else:
            r_count = GiveawayQueue.objects.filter(queue_type=queue_type, status='R').count()
            if r_count == 0:
                items = GiveawayQueue.objects.filter(queue_type=queue_type, status='W')
                if items.exists():
                    queue_launch(items[0].id)
        return True
    except Exception as e:
        print(e)
        return False


def queue_thread(name):
    while (1):
        # break
        process_queue('H')
        process_queue('D')
        process_queue('L')
        time.sleep(3)


def launch_thread():
    x = threading.Thread(target=queue_thread, args=(999999,))
    x.start()


launch_thread()


def add_queue(request, order_id, item_id):
    res = {'success': True, 'msg': ''}
    try:
        order_item = OrderItem.objects.get(id=item_id)
        queue_type = order_item.item.priority
        run_time = int(order_item.item.duration_to_run * request.user.account_type.time_quantifier)
        giveaway_amount = int(order_item.item.giveaway_value)
        GiveawayQueue.objects.create(user_id=request.user.id, order_id=order_id, item_id=item_id, duration=run_time,
                                     status='W', queue_type=queue_type, giveaway_amount=giveaway_amount)
        count = GiveawayQueue.objects.filter(queue_type=queue_type, status__in=['W', 'L', 'R']).count()
        if count == 1:
            res['msg'] = "Your giveaway is live soon!"
        else:
            res['msg'] = f"Your giveaway is in queue. Current position: {count}"
    except Exception as e:
        print(e)
        res['success'] = False
    return res


@cleared_hot_check
def launch_giveaway(request, order_id, item_id):
    context = {}
    try:
        order_item = OrderItem.objects.get(id=item_id)
        if order_item.available_to_run < 1:
            messages.error(request, "This order has already been redeemed.")
        else:
            res = add_queue(request, order_id, item_id)
            if res['success'] == True:
                decrease_available_giveaways(item_id)
                messages.success(request, res['msg'])
            else:
                messages.error(request, "Failed in adding into queue.")
    except Exception as e:
        messages.error(request, "Your giveaway could not be launched!")
        print(f"ERROR: {e}")
    return redirect("retweet_picker:giveaway-list")
    # return render(request, template_name='launch.html', context=context)


@csrf_exempt
def delete_queue(request):
    res = {'success': True, 'msg': 'Deleted successfully.'}
    queue_id = request.POST['queue_id']
    try:
        GiveawayQueue.objects.filter(id=queue_id).delete()
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while deleting queue.'
    return JsonResponse(res)

@csrf_exempt
def clear_queue(request):
    try:
        GiveawayQueue.objects.filter(status='E').delete()
        messages.success(request, 'Cleared successfully')
    except Exception as e:
        print(e)
        messages.error(request, "Failed to clear ended jobs")
    return redirect("retweet_picker:queue_view")

def prelaunch_validator(request, order_id, item_id):
    queryset = Order.objects.filter(ordered=True,
                                    id=request.user.id, kind=1).prefetch_related(
        Prefetch("items", queryset=OrderItem.objects.filter(item_id=item_id).select_related("item"),
                 to_attr='ordered_items'))
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
class QueueListView(ListView):
    template_name = "queue_list.html"
    model = GiveawayQueue

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # queue_type = self.kwargs.get('queue_type', 'default')
        # print("================ queue_type:", queue_type)
        rows = GiveawayQueue.objects.all()
        for row in rows:
            try:
                u = User.objects.get(id=row.user_id)
                row.username = u.username
            except Exception as e:
                print(e)
                row.username = ""
            try:
                order_item = OrderItem.objects.get(id=row.item_id)
                row.itemname = order_item.get_title()
            except Exception as e:
                print(e)
                row.itemname = ""
            if row.start_time == None:
                row.start_time = ''
            if row.end_time == None:
                row.end_time = ''
            if row.tweet_url == None:
                row.tweet_url = ''
                row.tweet_id = ''
            else:
                row.tweet_id = row.tweet_url.split('status/')[1]

        context['items'] = rows
        return context


@method_decorator(account_type_check, name='dispatch')
class OrdersListView(ListView):
    template_name = "command_center.html"
    model = Order
    ordering = ['-ordered_date']
    paginate_by = 20

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['order_items'] = order_items_prefetch_related_efficient(self.request.user.id)
        print(context)
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

def pick(request):
    context = {}
    try:
        context['giveaway_details'] = 'test'
    except Exception as e:
        pass

    return render(request, "pick.html", context)

@csrf_exempt
def draw(request):
    res = {'success': True, 'msg': ''}
    try:
        print(" === drawing .... ")
        link = request.POST['link']
        wc = int(request.POST['winner'])
        actions = {'follow_enable': False, 'follow_other': False}
        actions['draw_type'] = request.POST['draw_type']
        
        if request.POST['follow_enable'] == 'true':
            actions['follow_enable'] = True
        if request.POST['follow_other'] == 'true':
            actions['follow_other'] = True
        tags = request.POST['tags']
        sponsors = []
        if actions['follow_enable'] == True:
            username = request.user.username
            sponsors.append('@GridGamingIO')
            if actions['follow_other'] == True:
                user_list = tags.split(',')
                for tag in user_list:
                    sponsors.append("@" + tag)
        actions['sponsors'] = sponsors
        print("======== actions : ", actions)
        res = draw_winner(existing_tweet_url=link, winner_count=wc, actions=actions, user_id=request.user.id)
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while drawing.'
    return JsonResponse(res)

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
