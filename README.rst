Overview
========

This package enables you to run Django applications in their own
process space. It's designed for use with the PasteScript and
PasteDeploy packages.

Sample configuration::

  [app:django]
  use = egg:django-wsgi-process#app
  settings = %(here)s/settings.py

  [composite:main]
  use = egg:Paste#urlmap
  / = django

  [server:main]
  use = egg:Paste#http
  host = 0.0.0.0
  port = 8080

License
-------

This software is made available as-is under the BSD license.
