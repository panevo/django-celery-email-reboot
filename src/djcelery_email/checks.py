from importlib import metadata

from django.core.checks import Warning, register


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
