DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


INSTALLED_APPS = (
    'djcelery_email',
    'appconf',
)

SECRET_KEY = 'unique snowflake'

CELERY_EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_EMAIL_TASK_CONFIG = {
    'queue': 'django_email',
    'delivery_mode': 1,  # non persistent
    'rate_limit': '50/m',  # 50 chunks per minute
}
