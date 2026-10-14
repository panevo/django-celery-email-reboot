import pytest


@pytest.fixture(autouse=True)
def celery_email_backend(settings):
    # Django's test setup replaces EMAIL_BACKEND with the locmem backend, so send
    # all test mail through this package's backend instead.
    settings.EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
