from django.apps import AppConfig


class DjangoCeleryEmailConfig(AppConfig):
    name = 'djcelery_email'

    def ready(self):
        # Register system checks.
        from djcelery_email import checks  # noqa: F401
