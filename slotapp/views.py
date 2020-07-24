import json
import threading
import time
from datetime import timedelta
from django.utils import timezone

import paypalrestsdk
from decouple import config
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import UserProfile, Order, OrderItem, Slotitem, Checktime, Cartget, Payment, Item, History, Counting
from users.models import User, UserRoles
import random
import string

count_data = []
cart_get = []
brun = 0

paypalrestsdk.configure({
    "mode": config("PAYPAL_MODE"),  # sandbox or live
    "client_id": config("PAYPAL_CLIENT_ID"),
    "client_secret": config("PAYPAL_CLIENT_SECRET")})

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def setLaunch(value): 
    Checktime.objects.all().update(launched=value, launch_code=create_ref_code(), action_time=timezone.now())
    
def count_launch(name):
    release_time = 11
    launch_check = 0
    row = Checktime.objects.all()[0]
    launched = row.launched
    deadline = row.get_deadline()
    History.objects.create(action='Launched Thread ' + str(name), reason="")
    while (1):
        if release_time > 10:
            release_time = 0
            release_carts()
        if launch_check > 1:
            launch_check = 0
            row = Checktime.objects.all()[0]
            launched = row.launched
            deadline = row.get_deadline()
            if launched == False or deadline < timezone.now():
                break
        release_time += 1
        launch_check += 1
        time.sleep(1)
    setLaunch(False)
    History.objects.create(action='Close Launch Thread ' + str(name))
    
            
def launch_thread():
    launched = False
    thread_id = 1
    rows = Checktime.objects.all()
    if rows.count() > 0:
        launched = rows[0].launched
        thread_id = rows[0].thread_id
    else:
        Checktime.objects.create(launch_time=24)
        
    if launched == True:
        Checktime.objects.all().update(thread_id=thread_id+1)
        x = threading.Thread(target=count_launch, args=(thread_id,))
        x.start()
        
        
def initialize():
    History.objects.create(reason="Server restarted")
    History.objects.create(action='Launch', reason="server restart")
    launch_thread()
    print("\n========= server restarted ============\n")

initialize()
        
def docheck(user_id, kind, usernames=[], reason=""):
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
        History.objects.create(user=user, action='Purchased', item_str=order.get_purchased_items(),
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
        History.objects.create(user=user, action='Empty cart', item_str=order.get_purchased_items(), 
                               reason=reason, order_str=order.id)
        order.items.filter(kind=1, ordered=False, user=user).delete()
        Order.objects.filter(user=user, ordered=False, kind=1).delete()
        res['slots'] = data_list
        del_timing(user_id, "Empty command " + reason)
    
    return res


def release_carts():
    now = timezone.now() - timedelta(seconds=10)
    old_countings = Counting.objects.filter(deadline__lt=now)
    if old_countings.exists():
        temp = '[' + ','.join([str(x.order_id) for x in old_countings]) + ']'
        History.objects.create(action='Erase old countings', reason="Time over", order_str=temp)
        old_countings.delete()
        
    if not Counting.objects.all().exists():
        Checktime.objects.all().update(cartcounter_run=False)
            
    order_qs = Order.objects.filter(start_date__lt=now, ordered=False, kind=1)
    if not order_qs.exists():
        return
    for order in order_qs:  
        count_data = Counting.objects.filter(order_id=order.id)
        if not count_data.exists():
            docheck(order.user.id, 2, [], "By system")

def count_handle(name):
    brun = Checktime.objects.all()[0].cartcounter_run
    while (1):
        count_data = Counting.objects.all()
        if not count_data.exists():
            Checktime.objects.all().update(cartcounter_run=False)
            break

        for item in count_data:
            if item.pause == True:
                item.deadline = item.deadline + timedelta(seconds=1)
                item.save()
                continue
            if item.deadline < timezone.now():
                Cartget.objects.create(user_id=item.user_id)
                docheck(item.user_id, 2, [], "Time out")
        time.sleep(1)


def new_counter():
    row = Checktime.objects.all()[0]
    thread_id = row.thread_id
    brun = row.cartcounter_run
    if brun == False:
        Checktime.objects.all().update(thread_id=thread_id+1, cartcounter_run=True)
        x = threading.Thread(target=count_handle, args=(thread_id,))
        x.start()
        

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

@csrf_exempt
def test_adduser(request):
    roles = UserRoles.objects.filter(role_name="Content Creator")
    if roles.exists():
        role = roles[0]
        for i in range(5):
            User.objects.create(username="test" + str(i), password="test", account_type=role)
    return redirect("slotapp:test")

@login_required
def index(request):
    return redirect("slotapp:first_page")


def user_logout(request):
    logout(request)
    return HttpResponse("logout")


@login_required
def first_page(request):
    request.session['kind'] = 1
    user_id = request.user.id
    u = User.objects.get(id=user_id)
    slots = Slotitem.objects.filter(available=True)
    data = {'user': u, 'slots': slots, 'time': 0}
    
    res = removefromcart(user_id)
    count_data = Counting.objects.filter(user_id=user_id)
    if count_data.exists():
        if res['left'] == 0:
            count_data.delete()
            History.objects.create(user=request.user, action='Delete timer', reason="left is 0")
        else:
            count_data.update(pause=False)
            deadline = count_data[0].deadline
            remain = int((deadline - timezone.now()).total_seconds())
            data['time'] = remain
            
    launched = False
    launch_timer = 0
    rows = Checktime.objects.all()
    if rows.count() > 0:
        launched = rows[0].launched
        if launched:
            deadline = rows[0].get_deadline()
            launch_timer = int((deadline - timezone.now()).total_seconds())
    data['launched'] = launched
    data['launch_timer'] = launch_timer
    paypal_status = config("PAYPAL_STATUS_COMMUNITY")
    Cartget.objects.filter(user_id=user_id).delete()
    History.objects.create(user=request.user, action='Refresh', reason="GET Launched:" + str(launched) + " launch timer: " + str(data['launch_timer']))
    if res['removed'] == 1:
        messages.warning(request, res['msg'])
    return render(request, 'slotapp/first-page.html', {'data': data, 'paypal_status':paypal_status})

@csrf_exempt
def tocart(request):
    res = {'success': True, 'time_set': 0}
    user_id = request.user.id
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
                History.objects.create(user=user, action='To cart', order_str=order.id)

            order.items.add(order_item)     # first adding to cart
            item.available_count = item.available_count - 1

            item.save()
            res['kind'] = 0
            if cart_count == 0:
                cts = list(Checktime.objects.all())
                ct = 5
                if len(cts) > 0:
                    ct = cts[0].time
                deadline = timezone.now() + timedelta(minutes=ct)
                Counting.objects.create(user_id=user_id, pause=False, deadline=deadline, order_id=order.id)
                History.objects.create(user=request.user, action='Add to timer', order_str=str(order.id))
                res['time_set'] = 1
                res['time'] = ct * 60
                new_counter()
            
    res['available_count'] = item.available_count
    res['total'] = item.total
    
    return JsonResponse(res)


@csrf_exempt
def getcart(request):
    res = {'success': True}
    user_id = request.user.id
    ordered_list = []
    order_list = []

    Cartget.objects.filter(user_id=user_id).delete()

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
    count_data = Counting.objects.filter(user_id=user_id)
    if not count_data.exists():
        return
    temp = '[' + ','.join([str(x.order_id) for x in count_data]) + ']'
    user = get_userinstance(user_id)
    History.objects.create(user=user, action='Delete timer', reason=reason, order_str=temp)
    count_data.delete()

def get_userinstance(user_id):
    users = User.objects.filter(id=user_id)
    if len(users) > 0:
        return users[0]
    else:
        return None

@csrf_exempt
def cartminus(request):
    res = {'success': True, 'end_timing': False}
    user_id = request.user.id
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
    res = {'success': True}
    user_id = request.user.id
    cart_get = Cartget.objects.filter(user_id=user_id)
    if cart_get.exists():
        cart_get.delete()
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
    res['refresh'] = False 
    
    return JsonResponse(res)


@csrf_exempt
def setpause(request):
    res = {'success': True}
    user_id = request.user.id
    kind = request.POST['kind']
    count_data = Counting.objects.filter(user_id=user_id)
    if count_data.exists():
        count_data.update(pause=True if kind == '1' else False)
        deadline = count_data[0].deadline
        remain = int((deadline - timezone.now()).total_seconds())
        res['time'] = remain
    return JsonResponse(res)


@csrf_exempt
def checkout(request):
    user_id = request.user.id
    kind = request.POST['kind']
    usernames = request.POST['usernames']
    usernames = json.loads(usernames)
    res = docheck(user_id, kind, usernames)
    return JsonResponse(res)


@csrf_exempt
def slot_payment(request):
    user_id = request.user.id
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
    user_id = request.user.id
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
    value = request.GET.get('value', 0)
    setLaunch(True if value == '1' else False)
    if value == '1':
        History.objects.create(user=request.user, action='Launch', reason="By Mannual")
        launch_thread() # launch
    return redirect('./community')


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

@csrf_exempt
def setusernames(request):
    res = {'success': True}
    usernames = request.POST['usernames']
    usernames = json.loads(usernames)
    user = request.user
    order_qs = Order.objects.filter(user=user, ordered=False, kind=1)
    if not order_qs.exists():
        res['success'] = False
        res['msg'] = 'You have no active order of community giveaway'
        return res
    order = order_qs[0]
    launch_code = Checktime.objects.all()[0].launch_code
    for u in usernames:
        order.items.filter(kind=1, slot__id=u['id'], ordered=False, user=user).update(username=u['name'], launch_code=launch_code)

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
            
