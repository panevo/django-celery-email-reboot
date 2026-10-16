from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from djcelery_email.tasks import send_emails
from djcelery_email.utils import chunked, email_to_dict


class CeleryEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, *, using=None, **kwargs):
        # Django 6.1+ passes an alias when the backend is created from MAILERS.
        alias = kwargs.pop('alias', None)
        if alias is None:
            # Configured with EMAIL_BACKEND: any other arguments are passed on to
            # the backend set in CELERY_EMAIL_BACKEND.
            super().__init__()
            self.init_kwargs = kwargs
        else:
            # Configured with MAILERS: BaseEmailBackend reports unknown OPTIONS.
            super().__init__(alias=alias, **kwargs)
            # RemovedInDjango2028Warning: deprecated per-call options, such as the auth_user
            # of send_mail(), are passed on to the mailer in using.
            ignored = kwargs.get('_ignore_unknown_kwargs') or ()
            self.init_kwargs = {name: kwargs[name] for name in ignored if name in kwargs}
            _check_using(alias, using)

        # Django 6.1 deprecates fail_silently in BaseEmailBackend, so keep it here.
        self.fail_silently = fail_silently
        self.using = using

    def send_messages(self, email_messages):
        # Only pass using when it is set, so tasks queued by projects that use
        # EMAIL_BACKEND can still be handled by workers running older versions.
        task_kwargs = {'using': self.using} if self.using is not None else {}
        result_tasks = []
        for chunk in chunked(email_messages, settings.CELERY_EMAIL_CHUNK_SIZE):
            chunk_messages = [email_to_dict(msg) for msg in chunk]
            result_tasks.append(send_emails.delay(chunk_messages, self.init_kwargs, **task_kwargs))
        return result_tasks


def _check_using(alias, using):
    from django.core.mail import InvalidMailer, mailers

    if using is None:
        raise InvalidMailer("OPTIONS must define 'using' with the alias of the mailer that sends the email.",
                            alias=alias)
    if using == alias:
        raise InvalidMailer("'using' must refer to a different mailer.", alias=alias)
    if using not in mailers:
        raise InvalidMailer(f"'using' refers to undefined mailer {using!r}.", alias=alias)
