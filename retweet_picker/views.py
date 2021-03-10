import logging
import sys
import threading
import math
import json
from datetime import timedelta
from django.utils import timezone
from json import dumps

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
from .models import Membership, PricingPlan, GiveawayResults, TwitterGiveawayID, TwitterGiveaway, GiveawayStats, GiveawayQueue, DrawPrice, \
    GiveawayWinners, ContestUserParticipation, ContestUserAccounts
from .process import ProcessRetrievedTweets
from .tasks import start_giveaway_bg,\
    retrieve_tweets_choose_winner_job,\
    draw_winner,\
    fetch_content_from_url,\
    load_entry_task
from users.models import User
from retweet_picker.manager import GiveawayManager
from frontend.utils import *

import time
import django_rq
import random
import string

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
lock = threading.Lock()

def create_drawid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


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
        lock.acquire()
        row = GiveawayQueue.objects.get(id=queue_id)
        if row.status == 'L':
            return False
        row.status = 'L'
        row.save()
        lock.release()
        print("=== launching:", queue_id, ":", row.queue_type, ":", row.tweet_url, )
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
        lock.acquire()
        row = GiveawayQueue.objects.get(id=queue_id)
        if row.status == 'R':
            return False
        row.status = 'R'
        row.save()
        lock.release()
        print("=== retrieving:", queue_id, ":", row.queue_type, ":", row.tweet_url, )

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

def get_queue_count():
    try:
        dp = DrawPrice.objects.all().first()
        return dp.queue_count
    except Exception as e:
        print(e)
    return 1

def process_queue(queue_type):
    try:
        rows = GiveawayQueue.objects.filter(queue_type=queue_type, status='L')
        if rows.exists():
            for row in rows:
                if row.start_time is not None:
                    end_time = row.start_time + timedelta(minutes=row.duration)
                    if end_time < timezone.now():
                        queue_retrieve(row.id)
        r_count = GiveawayQueue.objects.filter(queue_type=queue_type, status__in=['R', 'L']).count()
        queue_count = get_queue_count()
        if r_count < queue_count:
            items = GiveawayQueue.objects.filter(queue_type=queue_type, status='W')[:queue_count-r_count]
            if items.exists():
                for item in items:
                    queue_launch(item.id)
        return True
    except Exception as e:
        print(e)
        return False


def queue_thread(name):
    while (1):
        break
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
        # print(context)
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

    #print(giveaway_ids)

    return render(request, "contest_results.html", context)


def pick(request):
    context = {}
    try:
        context['giveaway_details'] = 'test'
    except Exception as e:
        pass

    return render(request, "pick.html", context)


@csrf_exempt
def fetch_data(request):
    res = {'success': True, 'msg': '', 'kind': 0}
    try:
        link = request.POST['link']
        res = fetch_content_from_url(existing_tweet_url=link)
        res['kind'] = 0
        if res['success'] == True:
            print('=== author:', res['author'], ":", request.user.username)
            if res['author'] == request.user.username or request.user.is_staff == True:
                res['isauthor'] = True
            else:
                res['isauthor'] = False
                
            tgids = TwitterGiveawayID.objects.filter(tweet_url=res['tweet_url'])
            if tgids.exists():
                gws= GiveawayWinners.objects.filter(giveaway_id=tgids[0])
                if gws.exists():
                    if gws[0].status == 'W':
                        res['kind'] = 2 # already drawed
                        temp = {}
                        temp['draw_id'] = gws[0].draw_id
                        temp['draw_status'] = gws[0].status
                        temp['drawed_at'] = '' if gws[0].drawed_at == None else gws[0].drawed_at.strftime("%d %B, %Y")
                        temp['entries'] = gws[0].loaded_count
                        temp['winner_count'] = gws[0].winner_count
                        temp['rerolls'] = get_rerolls(gws[0].id)['rerolls']
                        temp['gwid'] = gws[0].id
                        res['draw_info'] = temp
                    else:
                        res['kind'] = 1 # to  draw
                    res['actions'] = {'winner': gws[0].winner_count, 'fe': gws[0].follow_main, 'followers': gws[0].followers, 'bot_chk': gws[0].bot_chk}
        
        if DrawPrice.objects.all().count() == 0:
            DrawPrice.objects.create(price=1)
        price = DrawPrice.objects.all()[0]
        res['free_max'] = price.free_max
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while fetching data. Please input correct url.'
    return JsonResponse(res)


@csrf_exempt
def import_contest(request):
    res = {'success': True, 'msg': ''}
    try:
        link = request.POST['link']
        actions = json.loads(request.POST['actions'])
        tgid, created = TwitterGiveawayID.objects.get_or_create(tweet_url=link)
        gw, created = GiveawayWinners.objects.get_or_create(giveaway_id=tgid)
        gw.user_id = request.user.id
        gw.winner_count = int(actions['winner'])
        gw.follow_main = actions['fe']
        gw.followers = actions['tags']
        gw.bot_chk = actions['bot_chk']
        gw.save()
        res['gwid'] = gw.id
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while importing data. Please input correct url.'
    return JsonResponse(res)

def pick_entries(request, gwid):
    if request.method == "GET":
        request.session['uoid'] = -1
        context = {}
        context['tab'] = request.GET.get('tab', 'download')
        try:
            gw = GiveawayWinners.objects.get(id=gwid)
            if request.user.id != gw.user_id and request.user.is_staff == False:
                messages.warning(request, "You are not allowed to visit this page.")
                return redirect("retweet_picker:pick")
            tgid = TwitterGiveawayID.objects.get(id=gw.giveaway_id_id)
            tweet_url = tgid.tweet_url
            dp = DrawPrice.objects.all().first()
            if gw.status == 'C' or gw.status == 'E':
                gm = GiveawayManager(new_giveaway=False, existing_tweet_url=tweet_url, api_index=1)
                ret_count = gm.tweet.retweet_count
                membership, created = Membership.objects.get_or_create(user_id=request.user.id)
                pp, created = PricingPlan.objects.get_or_create(plan=membership.plan)
                context['pay_price'] = 0
                context['unlimited_count'] = pp.unlimited_count
                context['left_times'] = pp.limit_times + membership.bonus_count - membership.done_count
                context['total_times'] = pp.limit_times + membership.bonus_count

                if ret_count <= dp.free_max:
                    context['pay_status'] = 0  # free to download
                else:
                    if gw.paid_count + dp.free_max >= ret_count:
                        context['pay_status'] = 1  # you have already paid
                    else:
                        # set_donemonth(membership.id)
                        # membership = Membership.objects.get(user_id=request.user.id)
                        if pp.unlimited_times == True:
                            context['pay_status'] = 2  # You can be free from unlimited membership
                        elif membership.done_count < pp.limit_times + membership.bonus_count:
                            if pp.limit_times == 0:
                                context['pay_status'] = 3  # you are free from bonus
                                context['left_times'] = membership.bonus_count
                            else:
                                context['pay_status'] = 4  # you are free from limited membership
                        else:
                            if pp.limit_times == 0:
                                context['pay_status'] = 6    # you must pay
                            elif membership.done_count >= pp.limit_times:
                                context['pay_status'] = 5   # you exceed count this month
                                context['left_times'] = 0
                            rest = ret_count - gw.paid_count - dp.free_max
                            pay_price = math.ceil(rest / dp.per_amount * dp.price)
                            context['pay_price'] = pay_price
                context['ret_count'] = ret_count
            else:
                rerolls_result = get_rerolls(gwid)     
                context['rerolls'] = rerolls_result['rerolls']
            draw_info = get_drawinformation(gwid)
            context['current_credit'] = get_credit_amount(request.user.id)
            context['loaded_count'] = gw.loaded_count
            context['paid_amount'] = gw.paid_count
            context['winner_count'] = gw.winner_count
            context['bot_chk'] = gw.bot_chk
            context['follow_main'] = gw.follow_main
            context['followers'] = gw.followers
            context['tweet_url'] = tweet_url
            context['draw_status'] = gw.status
            context['gwid'] = gwid
            context['drawprice_free_max'] = dp.free_max
            context['drawprice_per_amount'] = dp.per_amount
            context['drawprice_price'] = dp.price
            context['draw_info'] = draw_info['draw_info']
            context['context'] = dumps(context) 
            context['cc_per_usd'] = get_cc_per_usd()
        except Exception as e:
            print(e)
        return render(request, "contest.html", context)
    else:
        print("======= darw post")
        try:
            amount = int(request.POST.get('amount'))
            cc_per_usd = get_cc_per_usd()
            gwid = request.POST.get('gwid')
            current_credit = get_credit_amount(request.user.id)
            if current_credit < amount * cc_per_usd:
                messages.warning(request, "You have not enough credits.")
                return redirect("/retweet-picker/draw/" + str(gwid))
            
            dp = DrawPrice.objects.all().first()
            count = math.ceil(amount / dp.price * dp.per_amount)
            gw = GiveawayWinners.objects.get(id=gwid)
            gw.paid_count = gw.paid_count + count
            gw.save()
            membership, created = Membership.objects.get_or_create(user_id=request.user.id)
            membership.credit_amount = current_credit - amount * cc_per_usd
            membership.save()
            messages.success(request, "Successfully paid with credits.")
        except Exception as e:
            print(e)
            messages.warning(request, "Please try again.")
        return redirect("/retweet-picker/draw/" + str(gwid))
                            
@csrf_exempt
def load_entries(request):
    res = {'success': True, 'msg': ''}
    try:
        gwid = request.POST['gwid']
        pay_status = int(request.POST['pay_status'])
        GiveawayWinners.objects.filter(id=gwid).update(status='C', loaded_count=0)
        load_entry_task(gwid, request.user.id, pay_status, schedule=timezone.now())
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Downloading entries failed'
    return JsonResponse(res)


@csrf_exempt
def load_entry_progress(request):
    res = {'success': True, 'msg': '', 'load_status': 'C'}
    try:
        gwid = request.POST['gwid']
        gw = GiveawayWinners.objects.get(id=gwid)
        if gw.status == 'L':
            res['load_status'] = 'L'
            res['loaded_count'] = gw.loaded_count
        elif gw.status == 'E':
            res['load_status'] = 'E'
            res['load_error'] = gw.load_error
        else:
            if gw.toload_count != 0:
                res['progress'] = int(gw.loaded_count / gw.toload_count * 100)
            else:
                res['progress'] = 0
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while fetching data. Please input correct url.'
    return JsonResponse(res)


@csrf_exempt
def load_all_entries(request):
    res = {'success': True, 'msg': '', 'participants': [], 'ended': False}
    try:
        gwid = request.POST['gwid']
        gw = GiveawayWinners.objects.get(id=gwid)
        tgid = TwitterGiveawayID.objects.get(id=gw.giveaway_id_id)
        tweet_url = tgid.tweet_url
        cups = ContestUserParticipation.objects.filter(contest=tgid, kind=1)
        if cups.exists():
            participants = cups[0].contestants.all()
            for p in participants:
                temp = {'user_id': p.user_id, 
                        'screen_name': p.user_screen_name, 
                        'profile_img': p.profile_img, 
                        'account_created': p.account_created}
                res['participants'].append(temp)
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while loading all entries.'
    return JsonResponse(res)

def get_reroll_count(user_id):
    try:
        plan = Membership.objects.get(user_id=user_id).plan
        reroll_count = PricingPlan.objects.filter(plan=plan).first().reroll_count
        print("=== reroll_count:", reroll_count)
        return reroll_count
    except Exception as e:
        print(e)
    return 0
    
def get_drawinformation(gwid):
    res = {'success:': True, 'msg': '', 'draw_info': {}}
    try:
        gw = GiveawayWinners.objects.get(id=gwid)
        reroll_count = get_reroll_count(gw.user_id)
        res['draw_info']['draw_id'] = gw.draw_id
        res['draw_info']['draw_status'] = gw.status
        res['draw_info']['drawed_at'] = '' if gw.drawed_at == None else gw.drawed_at.strftime("%d %B, %Y")
        res['draw_info']['draw_id'] = gw.draw_id
        res['draw_info']['reroll_limit'] = reroll_count - gw.rerolled_count
        res['draw_info']['winners'] = []
        if gw.status == 'W':
            winners = gw.winner.all()
            for w in winners:
                res['draw_info']['winners'].append({'screen_name': w.user_screen_name,
                                                    'profile_img': w.profile_img})
    except Exception as e:
        print(e)
        res['success'] = False
        res['draw_info'] = {'draw_status': '', 'drawed_at': '', 'draw_id': '', 'winners': []}
    return res


@csrf_exempt
def draw(request):
    res = {'success': True,
           'msg': '',
           'stop': False}
    try:
        
        gwid = request.POST['gwid']
        gw = GiveawayWinners.objects.get(id=gwid)
        gw.command = 0
        gw.status = 'D'
        gw.save()
        tgid = TwitterGiveawayID.objects.get(id=gw.giveaway_id_id)
        tweet_url = tgid.tweet_url

        actions = {}
        actions['draw_type'] = request.POST['draw_type']
        actions['reroll_id'] = int(request.POST['reroll_id'])
        reroll_count = get_reroll_count(gw.user_id)
        if actions['draw_type'] == 'reroll':
            if  gw.rerolled_count >= reroll_count:
                res['success'] = False
                res['msg'] = "You have reached rerolling limit times. you can't reroll anymore."
                res['reroll_limit'] = 0
                return JsonResponse(res)
            
        sponsors = []
        if gw.followers != '':
            user_list = gw.followers.split(',')
            for tag in user_list:
                sponsors.append("@" + tag)
                
        actions['sponsors'] = sponsors
        actions['gwid'] = gwid
        res = draw_winner(existing_tweet_url=tweet_url, winner_count=gw.winner_count, actions=actions, user_id=gw.user_id)
        if res['success'] == True and res['stop'] == False:
            gw = GiveawayWinners.objects.get(id=gwid)
            gw.status = 'W'
            gw.rerolled_count += 1
            if gw.draw_id == None or gw.draw_id == '':
                gw.draw_id = create_drawid()
            gw.save()

        draw_info = get_drawinformation(gwid)
        res['draw_info'] = draw_info['draw_info']
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while drawing.'
        
    print("== final draw result : ", res)
    return JsonResponse(res)


@csrf_exempt
def drawstop(request):
    res = {'success': True, 'msg': '', 'stoped': False}
    try:
        gwid = request.POST['gwid']
        print("=== stop drawing : ", gwid)
        gw = GiveawayWinners.objects.get(id=gwid)
        gw.command = 1
        gw.save()
        if gw.status == 'S':
            res['stoped'] = True
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while stop drawing.'
    return JsonResponse(res)

def get_rerolls(gwid):
    res = {'success': True, 'msg': '', 'rerolls': []}
    try:
        gw = GiveawayWinners.objects.get(id=gwid)
        rerolls = gw.re_rolls.all()
        for reroll in rerolls:
            cuas = ContestUserAccounts.objects.filter(pk=reroll.contestant_id)
            temp = {'screen_name': '', 'profile_img': ''}
            if cuas.exists():
                cua = cuas[0]
                temp['screen_name'] = cua.user_screen_name
                temp['profile_img'] = cua.profile_img
            res['rerolls'].append({'id': reroll.id, 'reason': reroll.reason, 'kind': reroll.kind, 'user_info': temp})
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while getting rerolls.'
    
    return res

@csrf_exempt
def drawing_progress(request):
    res = {'success': True, 'msg': '', 'rerolls': []}
    try:
        gwid = request.POST['gwid']
        res = get_rerolls(gwid)
    except Exception as e:
        print(e)
        res['success'] = False
        res['msg'] = 'Error occured while stop drawing.'
    return JsonResponse(res)


def draw_result(request, draw_id):
    print("=== drawid", draw_id)
    # tgids = TwitterGiveawayID.objects.filter(tweet_url=draw_id)
    # if tgids.exists():
    #     gws = GiveawayWinners.objects.filter(giveaway_id=tgids[0], user_id=request.user.id)
    context = {'exist': True}
    gws = GiveawayWinners.objects.filter(draw_id=draw_id)
    if not gws.exists():
        context['exist'] = False
    else:
        gw = gws[0]
        context['draw_status'] = gw.status
        context['drawed_at'] = '' if gws[0].drawed_at == None else gws[0].drawed_at.strftime("%d %B, %Y")
        context['entries'] = gw.loaded_count
        context['winner_count'] = gw.winner_count
        context['rerolls'] = []
        rerolls = gw.re_rolls.all()
        for reroll in rerolls:
            cuas = ContestUserAccounts.objects.filter(pk=reroll.contestant_id)
            temp = {'screen_name': '', 'profile_img': ''}
            if cuas.exists():
                cua = cuas[0]
                temp['screen_name'] = cua.user_screen_name
                temp['profile_img'] = cua.profile_img
                context['rerolls'].append(
                    {'id': reroll.id, 'reason': reroll.reason, 'kind': reroll.kind, 'user_info': temp})
    context['context'] = dumps(context)
    return render(request, "draw_result.html", context)

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
