Overview
========

This package enables you to test, manage and run Django applications
in their own process space. It's designed for use with the PasteScript
and PasteDeploy packages.

Testing
-------

Simply inherit your test case class from
``dpt.testing.FunctionalTestCase`` instead of ``unittest.TestCase``.

This will cause the testrunner to start a new process and run the test
in isolation. Test results will appear exactly the same.

Note that this will set up the default Django settings environment
``django.conf.global_settings`` with a SQLite in-memory database.

Running an application
----------------------

For a general introduction to PasteDeploy consult its `documentation
<http://pythonpaste.org/deploy/>`_.

Sample configuration ``deploy.ini``::

  [app:my-django-app]
  use = egg:django-process-tools#app
  settings = %(here)s/settings.py

  [composite:main]
  use = egg:Paste#urlmap
  / = my-django-app

  [server:main]
  use = egg:Paste#http
  host = 0.0.0.0
  port = 8080

Note the reference to the ``settings.py`` file which in this example
resides in the same directory (the ``here`` variable is substituted
with the local directory).

To run the application we use `PasteScript
<http://pythonpaste.org/script/>`_ with the ``serve`` command::

  $ paster serve deploy.ini

Management
----------

The ``manage`` command mimicks Django's ``manage.py`` script. Here's
an example of an invocation of the ``syncdb`` command::

  $ paster manage deploy.ini my-django-app syncdb

To show all commands::

  $ paster manage deploy.ini my-django-app help

Note that if the application name is ``main`` (this short-hand is used
in general with the Paste system), the command is just::

  $ paster manage deploy.ini syncdb

Support
-------

This software is kept in source control: `git repository
<http://github.com/malthe/django-process-tools>`_.

For support please log on to ``irc.freenode.net`` and join
``#repoze``.

License
-------

This software is made available as-is under the BSD license.
