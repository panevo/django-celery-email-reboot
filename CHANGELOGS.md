# Changelogs

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

- [#4](https://github.com/panevo/django-celery-email-reboot/pull/4) Add support for Django 5.1, 5.2; Celery 5.3, 5.4, 5.5; Python 3.13. Drop support for Python 3.8.

## [4.0.1] - 2024-05-28

### Changed

- [#2](https://github.com/panevo/django-celery-email/pull/2) Update package details for PyPI

## [4.0.0] - 2024-05-22

* Support for Django 4.0+
* Support for Python 3.10+
* Support for Celery 5.2+
* Drop support for Django 2.2
* Drop support for Celery 4
* Drop support for Python 3.7

3.1.0 - 2021.09.21
------------------

* Support for Django 3.1
* Support for Celery 5

3.0.0 - 2019.12.10
------------------

* Support for Django 3.0
* Support for Python 3.8
* Droppped support for Django 1.x, Django 2.0 and Django 2.1
* Droppped support for Python 2.7

2.0.2 - 2019.05.29
------------------

* Reduce memory usage by running email_to_dict on chunks. Thanks `Paul Brown`_.
* Simplify dict_to_email for readability and efficiency. Thanks `Paul Brown`_.
* Update test matrix for supported versions of Django, Celery and Python. Thanks `James`_.

.. _Paul Brown: https://github.com/pawl
.. _James: https://github.com/jmsmkn

2.0.1 - 2018.18.27
------------------
* Fix bug preventing sending text/* encoded mime attachments. Thanks `Cesar Canassa`_.

.. _Cesar Canassa: https://github.com/canassa

2.0 - 2017.07.10
----------------
* Support for Django 1.11 and Celery 4.0
* Dropped support for Celery 2.x and 3.x
* Dropped support for Python 3.3

1.1.5 - 2016.07.20
------------------
* Support extra email attributes via CELERY_EMAIL_MESSAGE_EXTRA_ATTRIBUTES setting
* Updated version requirements in README


1.1.4 - 2016.01.19
------------------

* Support sending email with embedded images. Thanks `Georg Zimmer`_.
* Document CELERY_EMAIL_CHUNK_SIZE. Thanks `Jonas Haag`_.
* Add exception handling to email backend connection. Thanks `Tom`_.

.. _Georg Zimmer: https://github.com/georgmzimmer
.. _Tom: https://github.com/tomleo

1.1.3 - 2015.11.06
------------------

* Support setting celery.base from string. Thanks `Matthew Jacobi`_.
* Use six for py2/3 string compatibility. Thanks `Matthew Jacobi`_.
* Pass content_subtype back in for retries. Thanks `Mark Joshua Tan`_.
* Rework how tests work, add tox, rework travis-ci matrix.
* Use six from django.utils.
* Release a universal wheel.

.. _Matthew Jacobi: https://github.com/oppianmatt
.. _Mark Joshua Tan: https://github.com/mark-tan

1.1.2 - 2015.07.06
------------------

* Fix for HTML-only emails. Thanks `gnarvaja`_.

.. _gnarvaja: https://github.com/gnarvaja

1.1.1 - 2015.03.20
------------------

* Fix for backward compatibility of task kwarg handling - Thanks `Jeremy Thurgood`_.

.. _Jeremy Thurgood: https://github.com/jerith

1.1.0 - 2015.03.06
------------------

* New PyPI release rolling up 1.0.5 changes and some cleanup.
* More backward compatability in task. Will still accept message objects and lists of message objects.
* Thanks again to everyone who contributed to 1.0.5.

1.0.5 - 2014.08.24
------------------

* Django 1.6 support, Travis CI testing, chunked sending & more - thanks `Jonas Haag`_.
* HTML email support - thanks `Andres Riancho`_.
* Support for JSON transit for Celery, sponsored by `DigiACTive`_.
* Drop support for Django 1.2.

.. _`Jonas Haag`: https://github.com/jonashaag
.. _`Andres Riancho`: https://github.com/andresriancho
.. _`DigiACTive`: https://github.com/digiactive

1.0.4 - 2013.10.12
------------------

* Add Django 1.5.2 and Python 3 support.
* Thanks to `Stefan Wehrmeyer`_ for the contribution.

.. _`Stefan Wehrmeyer`: https://github.com/stefanw

1.0.3 - 2012.03.06
------------------

* Backend will now pass any kwargs with which it is initialized to the
  email sending backend.
* Thanks to `Fedor Tyurin`_ for the contribution.

.. _`Fedor Tyurin`: https://bitbucket.org/ftyurin


1.0.2 - 2012.02.21
------------------

* Task and backend now accept kwargs that can be used in signal handlers.
* Task now returns the result from the email sending backend.
* Thanks to `Yehonatan Daniv`_ for these changes.

.. _`Yehonatan Daniv`: https://bitbucket.org/ydaniv

1.0.1 - 2011.10.06
------------------

* Fixed a bug that resulted in tasks that were throwing errors reporting success.
* If there is an exception thrown by the sending email backend, the result of the task will
  now be this exception.
