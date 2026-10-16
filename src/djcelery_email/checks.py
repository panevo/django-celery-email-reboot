from importlib import metadata

from django.conf import settings
from django.core import mail
from django.core.checks import Error, Warning, register
from django.utils.module_loading import import_string


@register()
def check_conflicting_package(app_configs, **kwargs):
    # The original django-celery-email installs the same djcelery_email module,
    # so uninstalling it deletes this package's files as well.
    try:
        metadata.distribution('django-celery-email')
    except metadata.PackageNotFoundError:
        return []
    return [
        Warning(
            'django-celery-email is installed alongside django-celery-email-reboot.',
            hint=(
                'Both packages provide the djcelery_email module, so removing either one deletes '
                'files the other needs. Run "pip uninstall django-celery-email" and then '
                '"pip install --force-reinstall django-celery-email-reboot".'
            ),
            id='djcelery_email.W001',
        )
    ]


@register()
def check_mailers(app_configs, **kwargs):
    # Django 6.1+: report a CeleryEmailBackend mailer with invalid OPTIONS now, instead of when
    # the first email is sent.
    if not hasattr(mail, 'mailers') or not hasattr(settings, 'MAILERS'):
        return []
    from djcelery_email.backends import CeleryEmailBackend

    errors = []
    for alias, config in settings.MAILERS.items():
        try:
            backend = import_string(config.get('BACKEND', 'django.core.mail.backends.smtp.EmailBackend'))
        except ImportError:
            # Django reports the missing backend when the mailer is used.
            continue
        if not (isinstance(backend, type) and issubclass(backend, CeleryEmailBackend)):
            continue
        try:
            mail.mailers[alias]
        except mail.InvalidMailer as error:
            errors.append(Error(str(error), id='djcelery_email.E001'))
    return errors
