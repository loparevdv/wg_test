"""
WSGI config for wg_chess project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wg_chess.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
