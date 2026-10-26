"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# App Service 環境では config.production を使います。
# NOTE: wsgi.py と manage.py にも同様の設定があります。
settings_module = 'config.production' if 'WEBSITE_HOSTNAME' in os.environ else 'config.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_asgi_application()
