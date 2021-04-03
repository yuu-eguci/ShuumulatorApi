"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# App Service 環境では config.production を使います。
# NOTE: WEBSITE_HOSTNAME は App Service 環境のデフォルト環境変数です。
# NOTE: manage.py にも同様の設定があります。
settings_module = 'config.production' if 'WEBSITE_HOSTNAME' in os.environ else 'config.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
