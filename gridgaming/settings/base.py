import os
from decouple import config
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = config('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'users.apps.UsersConfig',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.twitter',
    # 'allauth.socialaccount.providers.twitch',
    # 'allauth.socialaccount.providers.mixer',
    'crispy_forms',
    'django_countries',
    'paypal.standard.ipn',
    'sweetify',
    'storages',
    'retweet_picker',
    'core',
    'django_rq',
    'scheduler',
    'frontend',
    'mathfilters',
    'slotapp',
    'giveaways',
    'profile_analyzer',
    'background_task',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gridgaming.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

redis_url = urlparse(
    os.environ.get('REDISTOGO_URL', 'redis://localhost:6959')
)
RQ_SHOW_ADMIN_LINK = True
# CACHES = {
#     'default': {
#         'BACKEND': 'redis_cache.RedisCache',
#         'LOCATION': '%s:%s' % (redis_url.hostname, redis_url.port),
#         'OPTIONS': {
#             'DB': 0,
#             'PASSWORD': redis_url.password,
#         }
#     }
# }


RQ_QUEUES = {
    'default': {
        'URL': os.getenv('REDISTOGO_URL', 'redis://localhost:6379/0'),  # If you're on Heroku
        'DB': 0,
        'PORT': 6379,
        'DEFAULT_TIMEOUT': 260000,
    },
    # 'with-sentinel': {
    #     'SENTINELS': [('localhost', 26736), ('localhost', 26737)],
    #     'MASTER_NAME': 'redismaster',
    #     'DB': 0,
    #     'PASSWORD': 'secret',
    #     'SOCKET_TIMEOUT': None,
    #     'CONNECTION_KWARGS': {
    #         'socket_connect_timeout': 0.3
    #     },
    # },
    'high': {
        'URL': os.getenv('REDISTOGO_URL', 'redis://localhost:6379/0'),  # If you're on Heroku
        'DB': 0,
        'PORT': 6379,
        'DEFAULT_TIMEOUT': 260000,
    },
    'low': {
        'URL': os.getenv('REDISTOGO_URL', 'redis://localhost:6379/0'),  # If you're on Heroku
        'DB': 0,
        'PORT': 6379,
        'DEFAULT_TIMEOUT': 260000,
    }
}

WSGI_APPLICATION = 'gridgaming.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media_root')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static_in_env')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEBUG_PROPAGATE_EXCEPTIONS = True

# Auth

# AUTHENTICATION_BACKENDS = (
#     'django.contrib.auth.backends.ModelBackend',
#     'allauth.account.auth_backends.AuthenticationBackend'
# )

# SITE_ID = 2 - first site

LOGIN_REDIRECT_URL = '/shop'
LOGOUT_REDIRECT_URL = '/frontend'
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login"

# CRISPY FORMS

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# PAYPAL_BUY_BUTTON_IMAGE = ''

GIVEAWAY_DAY_RANGE = 5

AUTH_USER_MODEL = 'users.User'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_PROVIDERS = {
    'twitter': {
        'SCOPE': ['email'],
    }
}
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
# BRAINTREE_MERCHANT_ID = config('BRAINTREE_MERCHANT_ID')
# BRAINTREE_PUBLIC_KEY = config('BRAINTREE_PUBLIC_KEY')
# BRAINTREE_PRIVATE_KEY = config('BRAINTREE_PRIVATE_KEY')

GIVEAWAY_TITLE_MAX_LENGTH = 350


# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_USE_TLS = True
# EMAIL_PORT = 587
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

BACKGROUND_TASK_RUN_ASYNC = True

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://eaec2f6715094d34a082eff3b358d344@o403453.ingest.sentry.io/5266107",
    integrations=[DjangoIntegration()],

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)
