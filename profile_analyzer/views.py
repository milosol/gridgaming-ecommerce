from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from .tasks import profile_checker


def analyze_profile(request):
    print(request)
    res = {'success': True, 'msg': '', 'profile_analysis': {}}
    print("HERE HERE HERE ANALYZE TIME")
    if request.method == 'GET':
        try:
            print("=== analyzing : ", request.user.username)
            profile_analysis = profile_checker(username=request.user.username)
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


