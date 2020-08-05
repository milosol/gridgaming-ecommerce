from .base import *
import dj_database_url

DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = ['*']
SITE_ID = 1

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

DATABASES = {}
DATABASES['default'] = dj_database_url.config(conn_max_age=600,
                                              default=config('DATABASE_URL'),
                                              ssl_require=True)


STRIPE_PUBLIC_KEY = config('STRIPE_LIVE_PUBLIC_KEY')
STRIPE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY')

PAYPAL_RECEIVER_EMAIL = config('PAYPAL_RECEIVER_EMAIL')
PAYPAL_TEST = False

BITPAY_TOKEN = 'FWUX5iqyA19qY1wVimA8eCW9shcVXNtjuQpX32BhbsRS'
BITPAY_TEST = False


# Store files in Amazon S3
AWS_LOCATION = 'static'
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN='%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
     'CacheControl': 'max-age=86400',
}

#STATIC_URL='https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# #STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

#END S3

WHITENOISE_MANIFEST_STRICT = False

# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static_in_env'),
# ]


AWS_DEFAULT_ACL = None


SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
