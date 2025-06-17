#!/usr/bin/env python
import os
import codecs

from setuptools import setup, find_packages


base_dir = os.path.dirname(__file__)

with codecs.open(os.path.join(base_dir, 'README.rst'), 'r', encoding='utf8') as f:
    long_description = f.read()

about = {}
with open(os.path.join(base_dir, 'djcelery_email', '__about__.py')) as f:
    exec(f.read(), about)


setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__summary__'],
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license=about['__license__'],
    url=about['__uri__'],
    author=about['__author__'],
    author_email=about['__email__'],
    platforms=['any'],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    scripts=[],
    zip_safe=False,
    python_requires='>=3.9,<3.14',
    install_requires=[
        # Celery for Python 3.9 to 3.11
        "celery>=5.2,<5.6; python_version >= '3.9' and python_version <= '3.11'",
        # Celery for Python 3.12 and 3.13
        "celery>=5.3,<5.6; python_version >= '3.12'",
        # Django for Python 3.9
        "Django>=3.2,<4.3; python_version == '3.9'",
        # Django for Python 3.10
        "Django>=4.0,<5.1; python_version == '3.10'",
        # Django for Python 3.11
        "Django>=4.1,<5.3; python_version == '3.11'",
        # Django for Python 3.12 and 3.13
        "Django>=4.2,<5.3; python_version >= '3.12'",
        # django-appconf
        "django-appconf",
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 5.0',
        'Framework :: Django :: 5.1',
        'Framework :: Django :: 5.2',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Topic :: Communications',
        'Topic :: Communications :: Email',
        'Topic :: System :: Distributed Computing',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
