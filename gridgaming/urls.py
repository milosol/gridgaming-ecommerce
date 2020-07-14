from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def bubble5000(request):
    response = redirect('https://gleam.io/competitions/pSzPy-bubble-rescue-5000-giveaway')
    return response

urlpatterns = [
    path('gridadmin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('shop/', include('core.urls', namespace='shop')),
    path('contests/', include('retweet_picker.urls', namespace='contests')),
    #path('slot/', include('slotapp.urls', namespace='slot')),
    path('django-rq/', include('django_rq.urls')),
    path('bubble5000/', bubble5000, name='bubble5000'),
    path('', include('frontend.urls', namespace='frontend'))
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
