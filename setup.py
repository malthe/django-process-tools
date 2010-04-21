#!/usr/bin/env python # -- coding: utf-8 --

__version__ = '0.1'

import os
import sys

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()
long_description = "\n\n".join((README, CHANGES))

version = sys.version_info[:3]

install_requires = [
    'PasteScript',
    'PasteDeploy',
    'Django',
    ]

setup(
    name="django-wsgi-process",
    version=__version__,
    description="Process-based WSGI application host for Django.",
    long_description=long_description,
    classifiers=[
       "Development Status :: 3 - Alpha",
       "Intended Audience :: Developers",
       "Programming Language :: Python",
      ],
    keywords="django multiprocess wsgi",
    author="Malthe Borch",
    author_email="mborch@gmail.com",
    install_requires=install_requires,
    license='BSD',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    tests_require = install_requires,
    entry_points="""
    [paste.app_factory]
    app = dwp.run:make_app

    [paste.global_paster_command]
    manage=dwp.scripts:Manage
    """,
    )

