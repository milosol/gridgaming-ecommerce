import json
import threading
import time
from datetime import datetime

import paypalrestsdk
from decouple import config
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import UserProfile, Order, OrderItem, Slotitem, Checktime, Payment, Item, History
from core.views import create_ref_code
from users.models import User

count_data = []
cart_get = []
thread_id = 1
brun = 0
blaunch_timer = 1 # close status
launch_timer = 0

paypalrestsdk.configure({
    "mode": config("PAYPAL_MODE"),  # sandbox or live
    "client_id": config("PAYPAL_CLIENT_ID"),
    "client_secret": config("PAYPAL_CLIENT_SECRET")})

History.objects.create(action_type='E', reason="Server restarted")
print("\n========= server restarted ============\n")

def docheck(user_id, kind, usernames=[], reason=""):
    global count_data
    res = {'success': True}

    user = User.objects.get(id=user_id)
    order_qs = Order.objects.filter(user=user, ordered=False, kind=1)
    if not order_qs.exists():
        del_timing(user_id, "No active order")
        res['success'] = False
        res['msg'] = "You have no order information."
        return res

    order = order_qs[0]
    if kind == '1':
        launch_code = Checktime.objects.all()[0].launch_code
        for u in usernames:
            order.items.filter(kind=1, slot__id=u['id'], ordered=False, user=user).update(ordered=True,
                                                                                          username=u['name'],
                                                                                          launch_code=launch_code)

        payment = Payment()
        payment.payment_method = 'P'
        payment.user = order.user
        payment.amount = order.get_total()
        payment.save()

        order.ordered = True
        order.status = 'P'
        order.payment = payment
        order.ref_code = create_ref_code()
        order.save()
        History.objects.create(user=user, action_type='P', item_str=order.get_purchased_items(),
                                reason=reason, order_str=order.id)
        del_timing(user_id, "Payment done")
    else:
        data_list = []
        order_items = order.items.filter(kind=1, ordered=False, user=user)
        for c in order_items:
            try:
                data = {}
                s = Slotitem.objects.get(id=c.slot.id)
                s.available_count = s.available_count + 1
                s.save()

                data['slot_id'] = s.id
                data['available_count'] = str(s.available_count) + " / " + str(s.total)
                data_list.append(data)
            except Slotitem.DoesNotExist:
                pass
        History.objects.create(user=user, action_type='E', item_str=order.get_purchased_items(), 
                               reason=reason, order_str=order.id)
        order.items.filter(kind=1, ordered=False, user=user).delete()
        Order.objects.filter(user=user, ordered=False, kind=1).delete()
        res['slots'] = data_list
        del_timing(user_id, "Empty cart command " + reason)
    
    return res


def release_carts(by_user):
    global count_data
    order_items = OrderItem.objects.filter(ordered=False, kind=1)
    users = []
    for item in order_items:
        if item.user.id not in users:
            bcounting = 0
            for cdata in count_data:
                if cdata['user_id'] == str(item.user.id) or cdata['user_id'] == item.user.id:
                    bcounting = 1
                    break
            if bcounting == 0:
                docheck(item.user.id, 2, [], "By " + by_user)
            users.append(item.user.id)



def count_handle(name):
    global count_data, brun
    brun = 1
    while (1):
        if len(count_data) == 0:
            brun = 0
            break
        for item in count_data:
            if item['pause'] == '1':
                continue
            item['remain_time'] -= 1
            if item['remain_time'] < 1:
                cart_get.append(item['user_id'])
                count_data.remove(item)
                docheck(item['user_id'], 2, [], "Time out")
        time.sleep(1)


def new_counter():
    global thread_id, brun
    if brun == 0:
        x = threading.Thread(target=count_handle, args=(thread_id,))
        x.start()
        thread_id += 1


def count_launch(name):
    global blaunch_timer, launch_timer
    while (1):
        if blaunch_timer == 1:
            break
        launch_timer -= 1
        if launch_timer <= 0:
            setLaunch(False)
            blaunch_timer = 1
            launch_timer = 0
            break
        time.sleep(1)


@csrf_exempt
def test(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect("slotapp:first_page")
        users = User.objects.all()
        return render(request, 'slotapp/index.html', {'data': users})
    else:
        user_id = request.POST['user_id']
        user = User.objects.get(id=user_id)
        login(request, user)
        res = {'success': True}
        return JsonResponse(res)


@login_required
def index(request):
    return redirect("slotapp:first_page")


def user_logout(request):
    logout(request)
    return HttpResponse("logout")


@login_required
def first_page(request):
    global cart_get, count_data, launch_timer, blaunch_timer
    user_id = request.user.id
    u = User.objects.get(id=user_id)
    slots = Slotitem.objects.filter(available=True)
    data = {'user': u, 'slots': slots, 'time': 0}
    
    res = removefromcart(user_id)
    for item in count_data:
        if  item['user_id'] == str(user_id):
            if res['left'] == 0:
                count_data.remove(item)
                History.objects.create(user=request.user, action_type='E', reason="Stop timing because left is 0")
            else:
                data['time'] = item['remain_time']
                item['pause'] = '0'
            break
        
    # if data['time'] == 0:
    #     if Order.objects.filter(user=request.user, ordered=False, kind=1).count() > 0:
    #         docheck(user_id, 2)
    # Order.objects.filter(user=request.user, kind=1, ordered=False).delete()
    # OrderItem.objects.filter(user=request.user, kind=1, ordered=False).delete()
    release_carts(u.username)

    launched = False
    rows = Checktime.objects.all()
    if rows.count() > 0:
        launched = rows[0].launched
    if launched == True and blaunch_timer == 1:
        History.objects.create(action_type='N', reason="By automatic when refresh")
        launch_thread()
    data['launched'] = launched
    data['launch_timer'] = launch_timer
    paypal_status = config("PAYPAL_STATUS_COMMUNITY")
    
    if res['removed'] == 1:
        messages.warning(request, res['msg'])
    return render(request, 'slotapp/first-page.html', {'data': data, 'paypal_status':paypal_status})

@csrf_exempt
def tocart(request):
    global count_data
    res = {'success': True, 'time_set': 0}
    user_id = request.POST['user_id']
    slot_id = request.POST['slot_id']
    item = Slotitem.objects.get(id=slot_id)
    user = User.objects.get(id=user_id)

    cart_count = OrderItem.objects.filter(user=user, ordered=False, kind=1).count()
    order_item, created = OrderItem.objects.get_or_create(
        slot=item,
        user=user,
        ordered=False,
        kind=1
    )
    if item.available_count == 0 and created:
        res['success'] = False
        res['msg'] = 'Slot is not available now.'
        res['kind'] = 2
        order_item.delete()
    else:
        if not created:
            order_item.quantity += 1
            order_item.save()
            res['kind'] = 1  # not first adding slot to cart
        else:
            order_qs = Order.objects.filter(user=request.user, ordered=False, kind=1)
            if order_qs.exists():
                order = order_qs[0]
            else:
                ordered_date = timezone.now()
                order = Order.objects.create(
                    user=request.user, ordered_date=ordered_date, kind=1)
                History.objects.create(user=user, action_type='T', order_str=order.id)

            order.items.add(order_item)     # first adding to cart
            item.available_count = item.available_count - 1

            item.save()
            res['kind'] = 0
            if cart_count == 0:
                cts = list(Checktime.objects.all())
                ct = 5
                if len(cts) > 0:
                    ct = cts[0].time
                count_data.append({'user_id': user_id, 'pause': 0, 'remain_time': ct * 20})
                res['time_set'] = 1
                res['time'] = ct * 20
            new_counter()
        # History.objects.create(user=user, action_type='T', item=order_item.quantity + " of " + order_item.slot.title)   
    res['available_count'] = item.available_count
    res['total'] = item.total
    
    return JsonResponse(res)


@csrf_exempt
def getcart(request):
    res = {'success': True}
    user_id = request.POST['user_id']
    ordered_list = []
    order_list = []

    if user_id in cart_get:
        cart_get.remove(user_id)

    order_qs = Order.objects.filter(user=request.user, ordered=False, kind=1)
    if order_qs.exists():
        order = order_qs[0]
        order_items = order.items.filter(kind=1)
        for order_item in order_items:
            slot = order_item.slot
            data = {}
            data['id'] = slot.id
            data['slot'] = slot.title
            data['points'] = slot.points * order_item.quantity
            data['sub_total'] = order_item.quantity * slot.value
            data['username'] = order_item.username
            if order_item.ordered:
                ordered_list.append(data)
            else:
                order_list.append(data)

    res['order_list'] = order_list
    res['ordered_list'] = ordered_list
    return JsonResponse(res)


def del_timing(user_id, reason):
    for item in count_data:
        if item['user_id'] == user_id:
            user = get_userinstance(user_id)
            History.objects.create(user=user, action_type='D', reason=reason)
            count_data.remove(item)

def get_userinstance(user_id):
    users = User.objects.filter(id=user_id)
    if len(users) > 0:
        return users[0]
    else:
        return None

@csrf_exempt
def cartminus(request):
    res = {'success': True, 'end_timing': False}
    user_id = request.POST['user_id']
    slot_id = request.POST['slot_id']
    kind = request.POST['kind']  # 1: trash 0: minus

    order_qs = Order.objects.filter(user=request.user, ordered=False, kind=1)
    if order_qs.exists():
        order = order_qs[0]
        order_items = order.items.filter(kind=1, slot__id=slot_id, ordered=False)
        if order_items.count() != 0:
            order_item = order_items[0]
            av = 0
            order_item.quantity = order_item.quantity - 1
            if order_item.quantity == 0 or kind == '1':
                order_item.delete()
                av = 1
            else:
                order_item.save()
            data = {}

            s = Slotitem.objects.get(id=slot_id)
            s.available_count = s.available_count + av
            s.save()

            data['slot_id'] = s.id
            data['available_count'] = s.available_count
            data['total'] = s.total
            res['av_data'] = data
        else:
            res['success'] = False
            res['msg'] = "This slot is not in your cart."

        if order.items.filter(kind=1).count() == 0:
            del_timing(user_id, "Cart is empty by minus")
            order.delete()
            res['end_timing'] = True
    else:
        res['success'] = False
        res['msg'] = "You have no order information now."

    return JsonResponse(res)


@csrf_exempt
def get_available(request):
    global cart_get, blaunch_timer
    res = {'success': True}
    user_id = request.POST['user_id']
    if user_id in cart_get:
        cart_get.remove(user_id)
        res['cart_refresh'] = 'yes'
    else:
        res['cart_refresh'] = 'no'
        
    slot_list = Slotitem.objects.filter(available=True).values()
    data_list = []
    for s in slot_list:
        data = {}
        data['slot_id'] = s['id']
        data['available_count'] = s['available_count']
        data['total'] = s['total']
        data_list.append(data)

    res['slots'] = data_list
    if blaunch_timer == 1:
        res['refresh'] = False
        # History.objects.create(user=request.user, action_type='F', reason="By launch")
    else:
        res['refresh'] = False 
    
    # res['time_now'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return JsonResponse(res)


@csrf_exempt
def setpause(request):
    global count_data
    res = {'success': True}
    user_id = request.POST['user_id']
    kind = request.POST['kind']
    for item in count_data:
        if item['user_id'] == user_id:
            item['pause'] = kind
            res['time'] = item['remain_time']
            break
    return JsonResponse(res)


@csrf_exempt
def checkout(request):
    user_id = request.POST['user_id']
    kind = request.POST['kind']
    usernames = request.POST['usernames']
    usernames = json.loads(usernames)
    res = docheck(user_id, kind, usernames)
    return JsonResponse(res)


@csrf_exempt
def slot_payment(request):
    user_id = request.POST['user_id']
    return_url = request.POST['return_url']
    cancel_url = request.POST['cancel_url']
    user = User.objects.get(id=user_id)
    order_qs = Order.objects.filter(user=user, ordered=False, kind=1)
    order = order_qs[0]
    order_items = order.items.filter(kind=1, ordered=False)
    amount = 0
    for order_item in order_items:
        slot = order_item.slot
        amount += order_item.quantity * slot.value
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url},
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "Pay Points",
                        "sku": "Giveaway",
                        "price": amount,
                        "currency": "USD",
                        "quantity": 1}]},
                "amount": {
                    "total": amount,
                    "currency": "USD"},
                "description": "This is the payment transaction description."}]})
        if payment.create():
            print("- - - - - - payment success")
        else:
            print(payment.error)
    except Exception as e:
        print(str(e))
    return JsonResponse({'paymentID': payment.id, 'amount': amount})


@csrf_exempt
def slot_payment_execute(request):
    resp = {'success': True}
    user_id = request.POST['user_id']
    usernames = request.POST['usernames']
    usernames = json.loads(usernames)
    payment = paypalrestsdk.Payment.find(request.POST['paymentID'])
    if payment.execute({'payer_id': request.POST['payerID']}):
        print("Execute success")
        amount = float(payment.transactions[0].amount.total)
        fee = float(payment.transactions[0].related_resources[0].sale.transaction_fee.value)
        resp['amount'] = round(amount, 2)
        docheck(user_id, '1', usernames, "Payment done")
        messages.success(request, "Order complete!")
    else:
        messages.warning(request, "Payment Failed!")
        resp['success'] = False
        resp['msg'] = payment.error
        print(payment.error)
    return JsonResponse(resp)


@login_required
def launch(request):
    global blaunch_timer, launch_timer
    value = request.GET.get('value', 0)
    setLaunch(True if value == '1' else False)
    if value == '1':
        History.objects.create(user=request.user, action_type='N', reason="By Mannual")
        launch_thread() # launch
    else:               # close
        blaunch_timer = 1
        launch_timer = 0
    return redirect('./community')


def launch_thread():
    global blaunch_timer, launch_timer, thread_id
    launch_time = 24
    rows = Checktime.objects.all()
    if rows.count() > 0:
        launch_time = rows[0].launch_time
    else:
        Checktime.objects.create(launch_time=launch_time)
    blaunch_timer = 0
    launch_timer = launch_time * 3600
    x = threading.Thread(target=count_launch, args=(thread_id,))
    x.start()
    thread_id += 1


def setLaunch(value):
    Checktime.objects.all().update(launched=value, launch_code=create_ref_code())
    
@csrf_exempt
def setdisable(request):
    res = {'success': True}
    kind = request.POST['kind']   # 0: regular 1:community
    item_id = request.POST['id']
    value = request.POST['value']  # 1: available 2:disable
    if value == '1':
        value = True
    else:
        value = False
    
    if kind == '0':
        Item.objects.filter(id=item_id).update(available=value)
    else:
        Slotitem.objects.filter(id=item_id).update(available=value)
        
    return JsonResponse(res)

def removefromcart(user_id):
    res = {'left': 0, 'msg': '', 'removed': 0}
    user = User.objects.get(id=user_id)
    order_qs = Order.objects.filter(user=user, ordered=False, kind=1)
    if not order_qs.exists():
        return res
    order = order_qs[0]
    order_items = order.items.filter(kind=1, slot__available=False)
    if len(order_items) > 0:
        res['removed'] = 1
        res['msg'] = "The item in your cart is no longer available and has been removed"
    order_items.delete()
    if len(order.items.all()) == 0:
        order.delete()
    else:
        res['left'] = 1
    return res
            
