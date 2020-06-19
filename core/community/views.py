from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import User, Cart, Slotitem, Checktime

import threading
import time

count_data = []
cart_get = []
thread_id = 1
brun = 0

def count_handle(name):
    global count_data, brun
    brun = 1
    while(1):
        if len(count_data) == 0:
            brun = 0
            break
        for item in count_data:
            item['remain_time'] -= 1
            print("---------", item['user_id'], item['remain_time'])
            if item['remain_time'] < 1:
                count_data.remove(item)
                cart_get.append(item['user_id'])
                docheck(item['user_id'], 2)
                print("----- time over----", item['user_id'])
        time.sleep(1)
        
def new_counter():
    global thread_id, brun
    if brun == 0:
        x = threading.Thread(target=count_handle, args=(thread_id,))
        x.start()
        thread_id += 1
        
def index(request):
    if request.method == "GET":
        if 'user_id' in request.session:
            return redirect(first_page)
        users = User.objects.all()
        return render(request, 'slotapp/index.html', {'data': users})
    else:
        user_id = request.POST['user_id']
        request.session['user_id'] = user_id
        res = {'success': True}
        return JsonResponse(res)

def logout(request):
    del request.session['user_id']
    return redirect(index)

def first_page(request):
    global cart_get
    if 'user_id' not in request.session:
        return redirect(index)
    
    user_id = request.session['user_id']
    u = User.objects.get(id=user_id)
    slots = Slotitem.objects.all()
    data = {'user': u, 'slots': slots}
    
    if user_id in cart_get:
        cart_get.remove(user_id)
    return render(request, 'slotapp/first-page.html', {'data': data})

def tocart(request):
    global count_data
    res = {'success': True}
    user_id = request.POST['user_id']
    slot_id = request.POST['slot_id']
    
    
    cart_count = Cart.objects.filter(user_id=user_id, status=0).count()
    if cart_count == 0:
        cts = list(Checktime.objects.all())
        ct = 5
        if len(cts) > 0:
            ct = cts[0].time
            print("-----time---", ct)
        count_data.append({'user_id': user_id, 'remain_time': ct * 20})
        new_counter()
    try:
        c = Cart.objects.get(user_id=user_id, slot_id=slot_id, status=0)
        c.count = c.count + 1
        c.save()
        res['kind'] = 1
    except Cart.DoesNotExist:
        s = Slotitem.objects.get(id=slot_id)
        if s.available == 0:
            res['success'] = False
            res['msg'] = 'Slot is not available now.'
            res['kind'] = 2
        else:
            s.available = s.available - 1
            s.save()
            new_values = {'user_id': user_id, 'slot_id': slot_id, 'status': 0, 'count': 1}
            obj = Cart(**new_values)
            obj.save()
            res['kind'] = 0
        res['available'] = str(s.available) + "/" + str(s.total) 
    return JsonResponse(res)

def getcart(request):
    res = {'success': True}
    user_id = request.POST['user_id']
    cart_list = Cart.objects.filter(user_id=user_id, status=0).values()
    data_list = []
    for c in cart_list:
        try:
            s = Slotitem.objects.get(id=c['slot_id'])
            data = {}
            data['slot'] = s.title
            data['points'] = s.points * c['count']
            data['sub_total'] = c['count'] * s.value
            data_list.append(data)
        except Slotitem.DoesNotExist:
            pass
    res['data'] = data_list 
    return JsonResponse(res)

def get_available(request):
    global cart_get
    res = {'success': True}
    user_id = request.POST['user_id']

    if user_id in cart_get:
        cart_get.remove(user_id)
        res['cart_refresh'] = True
        print("---is in cartget", user_id)
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

def checkout(request):
    user_id = request.POST['user_id']
    kind = request.POST['kind']
    res = docheck(user_id, kind)
    return JsonResponse(res)

def docheck(user_id, kind):
    global count_data
    res = {'success': True}
    
    for item in count_data:
        if  item['user_id'] == user_id:
            count_data.remove(item)
            
    if kind == '1':
        Cart.objects.filter(user_id=user_id, status=0).update(status=1)
    else:
        data_list = []
        cart_list = Cart.objects.filter(user_id=user_id, status=0).values()
        for c in cart_list:
            try:
                data = {}
                s = Slotitem.objects.get(id=c['slot_id'])
                s.available = s.available + 1
                s.save()
                data['slot_id'] = s.id
                data['available'] = str(s.available) + "/" + str(s.total)
                data_list.append(data)
            except Slotitem.DoesNotExist:
                pass
        Cart.objects.filter(user_id=user_id, status=0).delete()
        res['slots'] = data_list
    return res
        