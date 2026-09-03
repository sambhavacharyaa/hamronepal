"""WSGI entry point for cPanel's Phusion Passenger Python App hosting.

cPanel's "Setup Python App" looks for a module here (configured as this
project's "Application startup file") exposing a WSGI callable (the
"Application Entry point", "application"). This just points Passenger at
Django's real WSGI app, using the production settings module.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from config.wsgi import application  # noqa: E402
