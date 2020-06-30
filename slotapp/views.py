from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from users.models import User, UserRoles
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from core.models import UserProfile, Order, OrderItem, Slotitem, Checktime, Payment
from core.views import create_ref_code
import paypalrestsdk
from paypalrestsdk import Payout, ResourceNotFound
import threading
import time
import json

count_data = []
cart_get = []
thread_id = 1
brun = 0

paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": "ASCtaHgzeskcV4tEI9k3fzwI30wEHoiL7T4MNEUyJd6Z6wyvmieCLqVHMhwcWjXv8h_f1URMTDm8nDwl",
  "client_secret": "ECmhqDxOtaOh6hWHnB35QXI0IHTKkg20RuFbN8g-4oyTA-c1oez35x_NtCzIpnsJJu8P8Ikg5HFGOkqp" })


def create_users(request):
    user1 = User.objects.create_user('user1', 'user1@test.com', 'test')
    user2 = User.objects.create_user('user2', 'user2@test.com', 'test')
    user3 = User.objects.create_user('user3', 'user3@test.com', 'test')
    user1.save()
    user2.save()
    user3.save()
    up1 = UserProfile(user=user1)
    up2 = UserProfile(user=user2)
    up3 = UserProfile(user=user2)
    up1.save()
    up2.save()
    up3.save()
    return HttpResponse('<h1>Successfully created</h1>') 

def count_handle(name):
    global count_data, brun
    brun = 1
    while(1):
        if len(count_data) == 0:
            brun = 0
            break
        for item in count_data:
            if item['pause'] == '1':
                continue
            item['remain_time'] -= 1
            if item['remain_time'] < 1:
                count_data.remove(item)
                cart_get.append(item['user_id'])
                docheck(item['user_id'], 2)
        time.sleep(1)
        
def new_counter():
    global thread_id, brun
    if brun == 0:
        x = threading.Thread(target=count_handle, args=(thread_id,))
        x.start()
        thread_id += 1
        
def index(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect(first_page)
        users = User.objects.all()
        return render(request, 'slotapp/index.html', {'data': users})
    else:
        user_id = request.POST['user_id']
        user = User.objects.get(id=user_id)
        login(request, user)
        res = {'success': True}
        return JsonResponse(res)

def user_logout(request):
    logout(request)
    return redirect(index)

@login_required
def first_page(request):
    global cart_get, count_data
    # if not request.user.is_authenticated:
    #     return redirect(index)
    # user = User.objects.get(id=1)
    # login(request, user)
    user_id = request.user.id
    u = User.objects.get(id=user_id)
    slots = Slotitem.objects.all()
    data = {'user': u, 'slots': slots, 'time': 0}
    
    if user_id in cart_get:
        cart_get.remove(user_id)
        
    for item in count_data:
        if  item['user_id'] == str(user_id):
            data['time'] = item['remain_time']
            break
    launched = False
    launch_time = 24
    rows = Checktime.objects.all()
    if rows.count() > 0:
        launched = rows[0].launched
        launch_time = rows[0].launch_time
    data['launched'] = launched    
    data['launch_time'] = launch_time  
    return render(request, 'slotapp/first-page.html', {'data': data})

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
    
    if item.available == 0 and created:
        res['success'] = False
        res['msg'] = 'Slot is not available now.'
        res['kind'] = 2
        order_item.delete()
    else:
        if not created:
            order_item.quantity += 1
            order_item.save()
            res['kind'] = 1     # not first adding slot to cart
        else:
            order_qs = Order.objects.filter(user=request.user, ordered=False, kind=1)
            if order_qs.exists():
                order = order_qs[0]
            else:
                ordered_date = timezone.now()
                order = Order.objects.create(
                    user=request.user, ordered_date=ordered_date, kind=1)
            order.items.add(order_item)     # first adding to cart
            item.available = item.available - 1
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
            
    res['available'] = item.available
    res['total'] = item.total
    
    return JsonResponse(res)

@csrf_exempt
def getcart(request):
    res = {'success': True}
    user_id = request.POST['user_id']
    ordered_list = []
    order_list = []
    
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

def del_timing(user_id):
    for item in count_data:
        if  item['user_id'] == user_id:
            count_data.remove(item)
            
@csrf_exempt          
def cartminus(request):
    res = {'success': True, 'end_timing': False}
    user_id = request.POST['user_id']
    slot_id = request.POST['slot_id']
    kind = request.POST['kind'] # 1: trash 0: minus
    
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
            s.available = s.available + av
            s.save()
            
            data['slot_id'] = s.id
            data['available'] = s.available
            data['total'] = s.total
            res['av_data'] = data
        else:
            res['success'] = False
            res['msg'] = "This slot is not in your cart."
        
        if order.items.filter(kind=1).count() == 0:
            del_timing(user_id)
            res['end_timing'] = True
    else:
        res['success'] = False
        res['msg'] = "You have no order information now."
        
    return JsonResponse(res)
    
@csrf_exempt
def get_available(request):
    global cart_get
    res = {'success': True}
    user_id = request.POST['user_id']

    if user_id in cart_get:
        cart_get.remove(user_id)
        res['cart_refresh'] = True
    else:
        res['cart_refresh'] = False
        
    slot_list = Slotitem.objects.filter().values()
    data_list = []
    for s in slot_list:
        data = {}
        data['slot_id'] = s['id']
        data['available'] = s['available']
        data['total'] = s['total']
        data_list.append(data)
    res['slots'] = data_list 
    return JsonResponse(res)

@csrf_exempt
def setpause(request):
    global count_data
    res = {'success': True}
    user_id = request.POST['user_id']
    kind = request.POST['kind']
    for item in count_data:
        if  item['user_id'] == user_id:
            item['pause'] = kind
            res['time'] = item['remain_time']
            break
    return JsonResponse(res)

@csrf_exempt
def checkout(request):
    user_id = request.POST['user_id']
    kind = request.POST['kind']
    usernames = request.POST['usernames']
    usernames  = json.loads(usernames)
    res = docheck(user_id, kind, usernames)
    return JsonResponse(res)

def docheck(user_id, kind, usernames = []):
    global count_data
    res = {'success': True}
    
    for item in count_data:
        if  item['user_id'] == user_id:
            count_data.remove(item)
            break
    
    user = User.objects.get(id=user_id)
    order_qs = Order.objects.filter(user=user, ordered=False, kind=1)
    if not order_qs.exists():
        res['success'] = False
        res['msg'] = "You have no order information."     
        return res
    
    order = order_qs[0]
    if kind == '1':
        launch_code = Checktime.objects.all()[0].launch_code
        for u in usernames:
            order.items.filter(kind=1, slot__id=u['id'], ordered=False, user=user).update(ordered=True, username=u['name'], launch_code=launch_code)
        
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
    else:
        data_list = []
        order_items = order.items.filter(kind=1, ordered=False, user=user)
        for c in order_items:
            try:
                data = {}
                s = Slotitem.objects.get(id=c.slot.id)
                s.available = s.available + 1
                s.save()
                
                data['slot_id'] = s.id
                data['available'] = str(s.available) + "/" + str(s.total)
                data_list.append(data)
            except Slotitem.DoesNotExist:
                pass
        order.items.filter(kind=1, ordered=False, user=user).delete()
        res['slots'] = data_list
    return res


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
    usernames  = json.loads(usernames)
    payment = paypalrestsdk.Payment.find(request.POST['paymentID'])
    if payment.execute({'payer_id': request.POST['payerID']}):
        print("Execute success")
        amount = float(payment.transactions[0].amount.total)
        fee = float(payment.transactions[0].related_resources[0].sale.transaction_fee.value)
        print(" - - - - payment amount: ", amount, fee)
        resp['amount'] = round(amount, 2)
        docheck(user_id, '1', usernames)
    else:
        resp['success'] = False
        resp['msg'] = payment.error
        print(payment.error)
    return JsonResponse(resp)

@login_required
def launch(request):
    value = request.GET.get('value', 0)
    setLaunch(True if value == '1' else False)
    if value == '1':
        launch_time = 24
        rows = Checktime.objects.all()
        if rows.count() > 0:
            launch_time = rows[0].launch_time
        else:
            Checktime.objects.create(launch_time=launch_time)
    return redirect('./first-page')

def setLaunch(value):
    Checktime.objects.all().update(launched=value, launch_code=create_ref_code())
    
def launch_back():
    print("=============Bacgkrond launched===")
    setLaunch(False)