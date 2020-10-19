from django.shortcuts import render

# Create your views here.

def profile_analyzer(request):
    context = {}
    try:
        context['analyzer'] = 'test'
    except Exception as e:
        pass

    return render(request, "profile_analyzer.html", context)