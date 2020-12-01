from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']


if DEBUG:
    INSTALLED_APPS += [
        'debug_toolbar',
        'django_extensions',
    ]

    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]

    # DEBUG TOOLBAR SETTINGS

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]


    def show_toolbar(request):
        return True


    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TOOLBAR_CALLBACK': show_toolbar
    }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DEV_DB_NAME'),
        'USER': config('DEV_DB_USER'),
        'PASSWORD': config('DEV_DB_PASSWORD'),
        'HOST': config('DEV_DB_HOST'),
        'PORT': ''
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }

STRIPE_PUBLIC_KEY = config('STRIPE_TEST_PUBLIC_KEY')
STRIPE_SECRET_KEY = config('STRIPE_TEST_SECRET_KEY')

COINBASE_API_KEY = config('COINBASE_API_KEY')

BRAINTREE_PRODUCTION = False
BRAINTREE_ENVIRONMENT='sandbox'

#Used for bit coin acceptance
BITPAY_TOKEN = config('BITPAY_TOKEN')
BITPAY_TEST = config('BITPAY_TEST', cast=bool)

#PAYPAL_RECEIVER_EMAIL = 'sb-nckcy2223315@business.example.com'
PAYPAL_RECEIVER_EMAIL = 'sb-ufygx2384593@business.example.com'
PAYPAL_TEST = True

SITE_ID = 2