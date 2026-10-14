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
    # Avoid upper bounds on Python and Django: when a new release is excluded,
    # resolvers silently fall back to old versions of this package that are
    # broken on it instead of failing (#19). Django declares its own Python support.
    python_requires='>=3.10',
    install_requires=[
        # Celery 5.3 is the first release to support Python 3.12
        "celery>=5.2,<6; python_version < '3.12'",
        "celery>=5.3,<6; python_version >= '3.12'",
        "Django>=4.2",
        "django-appconf",
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 5.0',
        'Framework :: Django :: 5.1',
        'Framework :: Django :: 5.2',
        'Framework :: Django :: 6.0',
        'Framework :: Django :: 6.1',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Topic :: Communications',
        'Topic :: Communications :: Email',
        'Topic :: System :: Distributed Computing',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
