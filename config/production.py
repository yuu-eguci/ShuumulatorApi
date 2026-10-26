# AppService 環境用の設定。
import os

# NOTE: 無いと Did you install mysqlclient? と煽られます。
import pymysql
from django.core.exceptions import ImproperlyConfigured

from .settings import *

pymysql.install_as_MySQLdb()

DEBUG = False

# 本番では環境変数のキーが必須です。ランダム生成にはしません。
# NOTE: .env.example のダミー値や短いキーのままなら起動しません。
if not os.environ.get('DJANGO_SECRET_KEY'):
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production.')
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
if len(SECRET_KEY) < 50 or 'local-only-dummy' in SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be a unique value of at least 50 characters.')
if 'local-only-dummy' in SHUUMULATOR_LOGIN_CODE:
    raise ImproperlyConfigured('SHUUMULATOR_LOGIN_CODE must not be the example value.')

# Configure the domain name using the environment variable
# that Azure automatically creates for us.
# NOTE: 以前は WEB_BASE_URL (スキーム付きの URL) も入れていましたが、ホスト名と一致しないので外しました。
if 'WEBSITE_HOSTNAME' in os.environ:
    ALLOWED_HOSTS = [os.environ['WEBSITE_HOSTNAME'], *ALLOWED_HOSTS]

# HTTPS 用の設定です。App Service は X-Forwarded-Proto を付けて転送します。
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
# NOTE: includeSubDomains と preload はドメイン全体に長く効くので、デプロイ先を決めるときに判断します。
SILENCED_SYSTEM_CHECKS = ['security.W005', 'security.W021']

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

# MySQL の接続先は環境変数で指定します。
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DJANGO_DATABASE_NAME'],
        'USER': os.environ['DJANGO_DATABASE_USER'],
        'PASSWORD': os.environ['DJANGO_DATABASE_PASSWORD'],
        'HOST': os.environ['DJANGO_DATABASE_SERVER'],
        'PORT': '3306',
        'OPTIONS': {
            # NOTE: PyMySQL が読むのは "ca" です。以前の "ssl-ca" は無視され、サーバー証明書を検証していませんでした。
            #       CA ファイルが無ければ接続に失敗します。
            'ssl': {'ca': os.environ.get('DJANGO_DATABASE_SSL_CA', '/var/www/html/BaltimoreCyberTrustRoot.crt.pem')}
        }
    }
}
