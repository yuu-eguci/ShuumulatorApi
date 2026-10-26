"""2021 年版で壊れていた挙動の回帰テストです。"""
import contextlib
import io
import os
import subprocess
import sys
from decimal import Decimal
from unittest import mock

import jwt
from django.conf import settings
from django.test import SimpleTestCase

from app.models import StockLog, Trading, User
from app.tests.base import SYNTHETIC_LOGIN_CODE, ApiTestCase, utc


class LoginRegressionTests(ApiTestCase):

    def login(self, code=SYNTHETIC_LOGIN_CODE):
        return self.client.post('/api-token-auth/', {'code': code}, format='json')

    def test_login_code_comes_from_settings(self):
        with self.settings(SHUUMULATOR_LOGIN_CODE='another-synthetic-code'):
            self.assertEqual(self.login('another-synthetic-code').status_code, 200)
            self.assertEqual(self.login(SYNTHETIC_LOGIN_CODE).status_code, 403)

    def test_login_is_disabled_without_configured_code(self):
        with self.settings(SHUUMULATOR_LOGIN_CODE=''):
            self.assertEqual(self.login('').status_code, 403)

    def test_login_code_is_compared_in_constant_time(self):
        with mock.patch('app.auth.hmac.compare_digest', return_value=False) as compare_digest:
            self.assertEqual(self.login().status_code, 403)
        compare_digest.assert_called_once()

    def test_token_is_signed_with_django_settings_secret_key(self):
        with self.settings(SECRET_KEY='another-synthetic-secret-key-0123456789abcdefghij'):
            token = self.login().json()['token']
            jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            self.client.credentials(HTTP_AUTHORIZATION=f'JWT {token}')
            self.assertEqual(self.client.get('/api/v1/user/1/').status_code, 200)

    def test_malformed_body_returns_400(self):
        response = self.client.post('/api-token-auth/', 'not json', content_type='application/json')

        self.assertEqual(response.status_code, 400)

    def test_missing_or_non_string_code_returns_403(self):
        for body in [{}, {'code': None}, {'code': 123}, ['code']]:
            with self.subTest(body=body):
                response = self.client.post('/api-token-auth/', body, format='json')
                self.assertEqual(response.status_code, 403)

    def test_missing_user_returns_403(self):
        Trading.objects.filter(user_id=1).delete()
        User.objects.filter(id=1).delete()

        self.assertEqual(self.login().status_code, 403)

    def test_secrets_are_not_printed(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            token = self.login().json()['token']
            self.client.credentials(HTTP_AUTHORIZATION=f'JWT {token}')
            self.client.get('/api/v1/user/1/')

        self.assertNotIn(SYNTHETIC_LOGIN_CODE, stdout.getvalue())
        self.assertNotIn(token, stdout.getvalue())


class JWTRegressionTests(ApiTestCase):

    def test_malformed_token_returns_403(self):
        for token in ['not-a-jwt', 'a.b.c']:
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=f'JWT {token}')
                self.assertEqual(self.client.get('/api/v1/user/1/').status_code, 403)

    def test_token_without_exp_returns_403(self):
        token = jwt.encode({'user_id': 1}, settings.SECRET_KEY, algorithm='HS256')
        self.client.credentials(HTTP_AUTHORIZATION=f'JWT {token}')

        self.assertEqual(self.client.get('/api/v1/user/1/').status_code, 403)

    def test_token_with_invalid_user_id_returns_403(self):
        for user_id in ['abc', None, [1]]:
            with self.subTest(user_id=user_id):
                self.authorize(user_id)
                self.assertEqual(self.client.get('/api/v1/user/1/').status_code, 403)

    def test_user_list_route_does_not_crash(self):
        self.authorize()

        self.assertIn(self.client.get('/api/v1/user/').status_code, [404, 405])


class OwnershipTests(ApiTestCase):

    def test_other_users_data_is_forbidden(self):
        self.authorize(user_id=1)
        for path in ['/api/v1/portfolio/2/', '/api/v1/realized/2/', '/api/v1/realized/2/?each=day', '/api/v1/portfolio/02/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_own_data_is_allowed(self):
        self.authorize(user_id=2)

        response = self.client.get('/api/v1/realized/2/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_gain'], 1000.0)


class PortfolioRegressionTests(ApiTestCase):

    def test_current_price_is_latest_log_per_stock(self):
        # 銘柄ごとに記録回数が違っても、それぞれの最新価格を使います。
        StockLog.objects.create(stock=self.stock_a, price=Decimal('126.00'))
        StockLog.objects.create(stock=self.stock_a, price=Decimal('127.00'))
        self.authorize()

        tradings = self.client.get('/api/v1/portfolio/1/').json()['tradings']

        self.assertEqual([t['current_price'] for t in tradings], [127.0, None])
        Trading.objects.create(stock=self.stock_b, user=self.user1, buy=Decimal('1.00'), bought_at=utc(2021, 4, 3))
        tradings = self.client.get('/api/v1/portfolio/1/').json()['tradings']
        self.assertEqual([t['current_price'] for t in tradings], [127.0, None, 210.0])


class RealizedRegressionTests(ApiTestCase):

    def test_no_completed_tradings_returns_zeros(self):
        Trading.objects.filter(user_id=1, sell__isnull=False).delete()
        self.authorize()

        response = self.client.get('/api/v1/realized/1/?each=month')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'user_id': '1', 'each': 'month', 'realized': [], 'win_rate': 0, 'total_gain': 0, 'total_lost': 0,
        })

    def test_tradings_without_buy_or_sold_at_are_ignored(self):
        Trading.objects.create(stock=self.stock_a, user=self.user1, buy=None, sell=Decimal('1.00'), sold_at=utc(2021, 5, 1))
        Trading.objects.create(stock=self.stock_a, user=self.user1, buy=Decimal('1.00'), sell=Decimal('9.00'), sold_at=None)
        self.authorize()

        response = self.client.get('/api/v1/realized/1/?each=year')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_gain'], 80.55)
        self.assertEqual([r['label'] for r in response.json()['realized']], ['2020', '2021'])


class ServerErrorTests(ApiTestCase):

    def test_server_error_does_not_leak_details(self):
        self.client.raise_request_exception = False
        self.authorize()

        with mock.patch('app.views.fetch_keeping_tradings', side_effect=RuntimeError('synthetic-internal-detail')):
            response = self.client.get('/api/v1/portfolio/1/')

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'synthetic-internal-detail', response.content)
        self.assertNotIn(b'Traceback', response.content)


class SettingsTests(SimpleTestCase):
    """設定モジュールを別プロセスで読み込んで確認します。"""

    def run_python(self, code, **env):
        # NOTE: .env などから来た環境変数に左右されないよう、設定に関わる変数は消します。
        prefixes = ('DJANGO_', 'WEBSITE_', 'WEB_', 'SHUUMULATOR_')
        base_env = {k: v for k, v in os.environ.items() if not k.startswith(prefixes)}
        return subprocess.run(
            [sys.executable, '-c', code], env={**base_env, **env}, cwd=settings.BASE_DIR,
            capture_output=True, text=True, timeout=60, check=False,
        )

    def production_env(self, **env):
        return {
            'DJANGO_SETTINGS_MODULE': 'config.production',
            'WEBSITE_HOSTNAME': 'api.example.invalid',
            'WEB_BASE_URL': 'https://web.example.invalid',
            'DJANGO_DATABASE_NAME': 'synthetic', 'DJANGO_DATABASE_USER': 'synthetic',
            'DJANGO_DATABASE_PASSWORD': 'synthetic', 'DJANGO_DATABASE_SERVER': 'db.example.invalid',
            **env,
        }

    def test_secret_key_comes_from_environment(self):
        result = self.run_python(
            'import os, django; django.setup(); from django.conf import settings; '
            'print(settings.SECRET_KEY == os.environ["DJANGO_SECRET_KEY"])',
            DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY='synthetic-env-secret-key-0123456789',
        )

        self.assertEqual(result.stdout.strip(), 'True', result.stderr)

    def test_production_requires_secret_key(self):
        result = self.run_python('import django; django.setup()', **self.production_env())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)

    def test_production_rejects_unsafe_values(self):
        cases = [
            ('short', {'DJANGO_SECRET_KEY': 'too-short-synthetic-key'}),
            ('example key', {'DJANGO_SECRET_KEY': 'local-only-dummy-secret-key-replace-me-0000000000000000'}),
            ('example code', {
                'DJANGO_SECRET_KEY': 'synthetic-production-secret-key-' + 'x' * 40,
                'SHUUMULATOR_LOGIN_CODE': 'local-only-dummy-login-code',
            }),
        ]
        for name, env in cases:
            with self.subTest(name):
                result = self.run_python('import django; django.setup()', **self.production_env(**env))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ImproperlyConfigured', result.stderr)

    def test_production_database_tls_verifies_server_certificate(self):
        # NOTE: PyMySQL は ssl の "ca" だけを読みます。以前の "ssl-ca" は無視され、証明書を検証していませんでした。
        result = self.run_python(
            'import django; django.setup(); from django.conf import settings; '
            'print(settings.DATABASES["default"]["OPTIONS"]["ssl"])',
            **self.production_env(
                DJANGO_SECRET_KEY='synthetic-production-secret-key-' + 'x' * 40,
                DJANGO_DATABASE_SSL_CA='/synthetic/ca.pem',
            ),
        )

        self.assertEqual(result.stdout.strip(), "{'ca': '/synthetic/ca.pem'}", result.stderr)

    def test_production_passes_deploy_checks(self):
        result = self.run_python(
            'import sys; from django.core.management import execute_from_command_line; '
            'execute_from_command_line(["manage.py", "check", "--deploy", "--fail-level", "WARNING"])',
            **self.production_env(DJANGO_SECRET_KEY='synthetic-production-secret-key-' + 'x' * 40),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
