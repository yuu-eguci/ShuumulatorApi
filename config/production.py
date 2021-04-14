# AppService 環境用の設定。
from .settings import *
import os

# NOTE: 無いと Did you install mysqlclient? と煽られます。
import pymysql
pymysql.install_as_MySQLdb()

DEBUG = False

# Configure the domain name using the environment variable
# that Azure automatically creates for us.
ALLOWED_HOSTS = [
    os.environ['WEBSITE_HOSTNAME'],
    os.environ['WEB_BASE_URL'],
] if 'WEBSITE_HOSTNAME' in os.environ else []

# WhiteNoise configuration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Add whitenoise middleware after the security middleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # NOTE: django-cors-headers, For cors(Upper than CommonMiddleware)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    os.environ['WEB_BASE_URL'],
]

# NOTE: この設定はいろんなサイトに記載されているが、 Missing staticfiles manifest entry エラーを引き起こすので排除。
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# STATIC_ROOT は settings.py に定義済み。

# Configure Postgres database; the full username is username@servername,
# which we construct using the DBHOST value.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DJANGO_DATABASE_NAME'],
        'USER': os.environ['DJANGO_DATABASE_USER'],
        'PASSWORD': os.environ['DJANGO_DATABASE_PASSWORD'],
        'HOST': os.environ['DJANGO_DATABASE_SERVER'],
        'PORT': '3306',
        'OPTIONS': {
            'ssl': {'ssl-ca': '/var/www/html/BaltimoreCyberTrustRoot.crt.pem'}
        }
    }
}
