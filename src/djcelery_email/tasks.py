from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.utils.module_loading import import_string

from celery import shared_task

# Make sure our AppConf is loaded properly.
import djcelery_email.conf  # noqa
from djcelery_email.utils import dict_to_email, email_to_dict

# Messages *must* be dicts, not instances of the EmailMessage class
# This is because we expect Celery to use JSON encoding, and we want to prevent
# code assuming otherwise.

TASK_CONFIG = {'name': 'djcelery_email_send_multiple', 'ignore_result': True}
TASK_CONFIG.update(settings.CELERY_EMAIL_TASK_CONFIG)

# import base if string to allow a base celery task
if 'base' in TASK_CONFIG and isinstance(TASK_CONFIG['base'], str):
    from django.utils.module_loading import import_string
    TASK_CONFIG['base'] = import_string(TASK_CONFIG['base'])


@shared_task(**TASK_CONFIG)
def send_emails(messages, backend_kwargs=None, *, using=None, **kwargs):
    # backward compat: handle **kwargs and missing backend_kwargs
    combined_kwargs = {}
    if backend_kwargs is not None:
        combined_kwargs.update(backend_kwargs)
    combined_kwargs.update(kwargs)

    # backward compat: catch single object or dict
    if isinstance(messages, (EmailMessage, dict)):
        messages = [messages]

    # make sure they're all dicts
    messages = [email_to_dict(m) for m in messages]

    if using is None and _mailers_configured():
        # Queued with EMAIL_BACKEND before the project switched to MAILERS.
        using = _mailer_for_tasks_without_using()
    if using is None:
        # Configured with EMAIL_BACKEND. Create the backend like get_connection() does,
        # which Django 6.1 deprecates.
        conn = import_string(settings.CELERY_EMAIL_BACKEND)(**combined_kwargs)
    else:
        # Configured with MAILERS (Django 6.1+): send through the wrapped mailer.
        conn = mail.mailers[using]
    try:
        conn.open()
    except Exception:
        if using is None:
            logger.exception("Cannot reach CELERY_EMAIL_BACKEND %s", settings.CELERY_EMAIL_BACKEND)
        else:
            logger.exception("Cannot reach mailer %r", using)

    messages_sent = 0

    for message in messages:
        try:
            sent = conn.send_messages([dict_to_email(message)])
            if sent is not None:
                messages_sent += sent
            logger.debug("Successfully sent email message to %r.", message['to'])
        except Exception as e:
            # Not expecting any specific kind of exception here because it
            # could be any number of things, depending on the backend
            logger.warning("Failed to send email message to %r, retrying. (%r)",
                           message['to'], e)
            retry_kwargs = {'using': using} if using is not None else None
            send_emails.retry([[message], combined_kwargs], kwargs=retry_kwargs, exc=e, throw=False)

    conn.close()
    return messages_sent


def _mailers_configured():
    return hasattr(mail, 'mailers') and hasattr(settings, 'MAILERS')


def _mailer_for_tasks_without_using():
    # Send through the mailer that the default CeleryEmailBackend mailer wraps, or else
    # through the default mailer.
    from djcelery_email.backends import CeleryEmailBackend

    default = mail.mailers.default
    return default.using if isinstance(default, CeleryEmailBackend) else 'default'


# backwards compatibility
SendEmailTask = send_email = send_emails


try:
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
except ImportError:
    logger = send_emails.get_logger()
