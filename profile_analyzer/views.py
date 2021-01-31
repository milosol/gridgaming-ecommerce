from django.http import JsonResponse
from django.shortcuts import render
# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from .tasks import profile_checker
from profile_analyzer.models import ProfileAnalysis, ProfileJudgement
from frontend.utils import *

def analyze_profile(request):
    print(request)
    res = {'success': True, 'msg': '', 'profile_analysis': {}}
    if request.method == 'GET':
        try:
            profile_analysis = profile_checker(username=request.user.username)
            if profile_analysis:
                res['profile_analysis'].update(profile_analysis)
                amount = get_judge_credit_price()
                current_amount = credit_minus(request.user.id, amount)
                res['current_credit'] = current_amount
            else:
                res['success'] = False
                res['msg'] = 'This profile could not be analyzed.'
        except Exception as e:
            res['success'] = False
            res['msg'] = 'This profile could not be analyzed.'
            
    return JsonResponse(res)

from .utils import update_or_create_analyzer

def profile_judgement(request):
    res = {'success': True, 'msg': '', 'profile_analysis': {}}
    print("Making Prediction")
    if request.method == 'GET':
        try:
            print("=== analyzing : ", request.user.username)
            profile_analysis = profile_checker(username=request.user.username)

            #Update request
            obj = update_or_create_analyzer(request.user, profile_analysis)

            #profile_analysis.bot_prediction
            if profile_analysis:
                res['profile_analysis'].update(profile_analysis)

        except Exception as e:
            print(e)
            res['success'] = False
            res['msg'] = 'This profile could not be analyzed.'
    return JsonResponse(res)

def main(request):
    context = {}
    try:
        context['analyzer'] = 'test'
    except Exception as e:
        pass

    return render(request, "profile_analyzer.html", context)



def reroll_decision(request):
    context = {}
    current_credit = get_credit_amount(request.user.id)
    credit_price = get_judge_credit_price()
    obj, created = ProfileJudgement.objects.get_or_create(user=request.user)

    context = {
        'current_credit': current_credit,
        'credit_price': credit_price
    }

    return render(request, "reroll_decision.html", context)


