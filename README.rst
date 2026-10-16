===========================================================================
django-celery-email-reboot - A Celery-backed Django Email Backend
===========================================================================

.. image:: https://img.shields.io/pypi/v/django-celery-email-reboot.svg?cacheSeconds=3600
    :target: https://pypi.org/project/django-celery-email-reboot/

A `Django`_ email backend that uses a `Celery`_ queue for out-of-band sending of the messages.

This is a fork of `django_celery_email`_. As this package has gone unmaintained for some time, we have decided to maintain the package in order to maintain compatibility with future Django versions, starting with Django 4.x, 5.x and 6.x.

This new package is available in pypi under the name `django-celery-email-reboot`: https://pypi.org/project/django-celery-email-reboot/

.. _`Celery`: http://celeryproject.org/
.. _`Django`: http://www.djangoproject.org/
.. _`django_celery_email`: https://github.com/pmclanahan/django-celery-email

.. warning::

    This version requires the following versions:

    * Python >= 3.10
    * Celery >= 5.2, < 6 (>= 5.3 on Python 3.12 and newer)
    * Django >= 4.2 (tested with 4.2, 5.0, 5.1, 5.2, 6.0 and 6.1)

Using django-celery-email-reboot
==================================

Install from Pypi using::

    pip install django-celery-email-reboot

If you are switching from the original ``django-celery-email``, uninstall it first. Both packages
install the same ``djcelery_email`` module, so uninstalling ``django-celery-email`` afterwards also
deletes the files of this package::

    pip uninstall django-celery-email
    pip install django-celery-email-reboot

If both packages are installed, a system check warning (``djcelery_email.W001``) is shown.

To enable ``django-celery-email-reboot`` for your project you need to add ``djcelery_email`` to
``INSTALLED_APPS``::

    INSTALLED_APPS += ("djcelery_email",)

You must then set ``django-celery-email`` as your ``EMAIL_BACKEND``::

    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

By default ``django-celery-email`` will use Django's builtin ``SMTP`` email backend
for the actual sending of the mail. If you'd like to use another backend, you
may set it in ``CELERY_EMAIL_BACKEND`` just like you would normally have set
``EMAIL_BACKEND`` before you were using Celery. In fact, the normal installation
procedure will most likely be to get your email working using only Django, then
change ``EMAIL_BACKEND`` to ``CELERY_EMAIL_BACKEND``, and then add the new
``EMAIL_BACKEND`` setting from above.

Using ``MAILERS`` (Django 6.1+)
-------------------------------

Django 6.1 replaces the ``EMAIL_BACKEND`` setting with ``MAILERS``. To use
``django-celery-email-reboot`` with ``MAILERS``, set ``CeleryEmailBackend`` as the ``BACKEND`` of a
mailer and set the ``using`` option to the alias of the mailer that should send the email::

    MAILERS = {
        "default": {
            "BACKEND": "djcelery_email.backends.CeleryEmailBackend",
            "OPTIONS": {
                "using": "smtp",
            },
        },
        "smtp": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": "smtp.example.com",
            },
        },
    }

When ``MAILERS`` is used, the ``CELERY_EMAIL_BACKEND`` setting is ignored. The email is sent from the
Celery worker through the mailer set in ``using``, so the workers need the same ``MAILERS`` setting.
The other ``CELERY_EMAIL_*`` settings described below still apply.

A ``CeleryEmailBackend`` mailer with invalid ``OPTIONS``, such as a missing ``using``, is reported by
Django's system checks (``djcelery_email.E001``).

Email that was queued before a project switched from ``EMAIL_BACKEND`` to ``MAILERS`` is sent through
the mailer that the default ``CeleryEmailBackend`` mailer wraps, or through the default mailer if it is
not a ``CeleryEmailBackend``.

Mass email are sent in chunks of size ``CELERY_EMAIL_CHUNK_SIZE`` (defaults to 10).

If you need to set any of the settings (attributes) you'd normally be able to set on a
`Celery Task`_ class had you written it yourself, you may specify them in a ``dict``
in the ``CELERY_EMAIL_TASK_CONFIG`` setting::

    CELERY_EMAIL_TASK_CONFIG = {
        'queue' : 'email',
        'rate_limit' : '50/m',  # * CELERY_EMAIL_CHUNK_SIZE (default: 10)
        ...
    }

There are some default settings. Unless you specify otherwise, the equivalent of the
following settings will apply::

    CELERY_EMAIL_TASK_CONFIG = {
        'name': 'djcelery_email_send',
        'ignore_result': True,
    }

After this setup is complete, and you have a working Celery install, sending
email will work exactly like it did before, except that the sending will be
handled by your Celery workers::

    from django.core import mail

    emails = (
        ('Hey Man', "I'm The Dude! So that's what you call me.", 'dude@aol.com', ['mr@lebowski.com']),
        ('Dammit Walter', "Let's go bowlin'.", 'dude@aol.com', ['wsobchak@vfw.org']),
    )
    results = mail.send_mass_mail(emails)

``results`` will be a list of celery `AsyncResult`_ objects that you may ignore, or use to check the
status of the email delivery task, or even wait for it to complete if want. You have to enable a result
backend and set ``ignore_result`` to ``False`` in ``CELERY_EMAIL_TASK_CONFIG`` if you want to use these.
You should also set ``CELERY_EMAIL_CHUNK_SIZE = 1`` in settings if you are concerned about task status
and results.

See the `Celery docs`_ for more info.


``len(results)`` will be the number of emails you attempted to send divided by CELERY_EMAIL_CHUNK_SIZE, and is in no way a reflection on the success or failure
of their delivery.

.. _`Celery Task`: http://celery.readthedocs.org/en/latest/userguide/tasks.html#basics
.. _`Celery docs`: http://celery.readthedocs.org/en/latest/userguide/tasks.html#task-states
.. _`AsyncResult`: http://celery.readthedocs.org/en/latest/reference/celery.result.html#celery.result.AsyncResult
