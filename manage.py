#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""

    # App Service 環境では config.production を使います。
    # NOTE: WEBSITE_HOSTNAME は App Service 環境のデフォルト環境変数です。
    # NOTE: wsgi.py にも同様の設定があります。
    settings_module = 'config.production' if 'WEBSITE_HOSTNAME' in os.environ else 'config.settings'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
