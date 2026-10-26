"""2021 年版 API の挙動を固定するテストです。Web 側との互換性のため、ここが変わってはいけません。"""
import time

import jwt
from django.conf import settings

from app.tests.base import SYNTHETIC_LOGIN_CODE, ApiTestCase, make_token


class LoginTests(ApiTestCase):

    def test_correct_code_returns_token_for_user_1(self):
        response = self.client.post('/api-token-auth/', {'code': SYNTHETIC_LOGIN_CODE}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.json()), ['token'])
        payload = jwt.decode(response.json()['token'], settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['user_id'], 1)
        self.assertAlmostEqual(payload['exp'], time.time() + 3600, delta=10)

    def test_wrong_code_returns_403(self):
        response = self.client.post('/api-token-auth/', {'code': 'wrong-code'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'detail': 'Authentication failed!!!'})


class JWTAuthenticationTests(ApiTestCase):

    def test_valid_token_returns_hello(self):
        self.authorize()

        response = self.client.get('/api/v1/user/1/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'hello': True})

    def test_user_endpoint_ignores_pk(self):
        # NOTE: ログイン確認だけの API で、 pk のユーザーのデータは返しません。
        self.authorize()
        for path in ['/api/v1/user/2/', '/api/v1/user/abc/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).json(), {'hello': True})

    def test_missing_token_returns_403(self):
        for path in ['/api/v1/user/1/', '/api/v1/portfolio/1/', '/api/v1/realized/1/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_rejected_tokens_return_403_with_message(self):
        cases = [
            ('JWT', 'Authorization 無効'),
            ('JWT a b', 'Authorization 無効 スペースはない'),
            (f'JWT {make_token(1, expires_in=-60)}', 'tokenはtimeout'),
            (f'JWT {make_token(1, key="another-synthetic-key-0123456789abcdef")}', 'InvalidSignatureError'),
            (f'JWT {make_token(999)}', 'ユーザー存在しません'),
        ]
        for header, message in cases:
            with self.subTest(message=message):
                self.client.credentials(HTTP_AUTHORIZATION=header)
                response = self.client.get('/api/v1/user/1/')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {'detail': message})


class PortfolioTests(ApiTestCase):

    def test_list_is_empty(self):
        self.authorize()

        self.assertEqual(self.client.get('/api/v1/portfolio/').json(), [])

    def test_non_numeric_user_id_returns_400(self):
        self.authorize()

        response = self.client.get('/api/v1/portfolio/abc/')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'')

    def test_retrieve_returns_keeping_tradings(self):
        self.authorize()

        response = self.client.get('/api/v1/portfolio/1/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'tradings': [
                {
                    'code': '1001', 'name': 'Synthetic A', 'buy': 120.0,
                    'bought_at': '2021-04-01T00:00:00Z', 'current_price': 125.0,
                },
                {
                    'code': '1003', 'name': 'Synthetic C', 'buy': 50.0,
                    'bought_at': '2021-04-02T00:00:00Z', 'current_price': None,
                },
            ],
        })


class RealizedTests(ApiTestCase):

    def get(self, query=''):
        self.authorize()
        return self.client.get(f'/api/v1/realized/1/{query}')

    def assert_realized(self, response, each, realized):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'user_id': '1',
            'each': each,
            'realized': realized,
            'win_rate': 5 / 7,
            'total_gain': 80.55,
            'total_lost': 29.5,
        })

    def test_list_is_empty(self):
        self.authorize()

        self.assertEqual(self.client.get('/api/v1/realized/').json(), [])

    def test_default_each_is_year(self):
        self.assert_realized(self.get(), 'year', [
            {'gain': 50.0, 'lost': 0, 'label': '2020'},
            {'gain': 30.55, 'lost': 29.5, 'label': '2021'},
        ])

    def test_each_month(self):
        self.assert_realized(self.get('?each=month'), 'month', [
            {'gain': 50.0, 'lost': 0, 'label': '2020-12'},
            {'gain': 30.25, 'lost': 29.5, 'label': '2021-1'},
            {'gain': 0.3, 'lost': 0, 'label': '2021-3'},
        ])

    def test_each_week_uses_iso_week_inside_month(self):
        self.assert_realized(self.get('?each=week'), 'week', [
            {'gain': 50.0, 'lost': 0, 'label': '2020-12-53'},
            {'gain': 0, 'lost': 19.5, 'label': '2021-1-53'},
            {'gain': 30.25, 'lost': 10.0, 'label': '2021-1-1'},
            {'gain': 0.3, 'lost': 0, 'label': '2021-3-13'},
        ])

    def test_each_day(self):
        self.assert_realized(self.get('?each=day'), 'day', [
            {'gain': 50.0, 'lost': 0, 'label': '2020-12-53-30'},
            {'gain': 0, 'lost': 19.5, 'label': '2021-1-53-1'},
            {'gain': 30.25, 'lost': 10.0, 'label': '2021-1-1-4'},
            {'gain': 0.3, 'lost': 0, 'label': '2021-3-13-31'},
        ])

    def test_zero_without_trades_is_integer_and_decimals_are_exact(self):
        realized = self.get('?each=week').json()['realized']

        # 損失のみ・利益のみのグループの 0 は int のまま JSON に出ます。
        self.assertIs(type(realized[1]['gain']), int)
        self.assertIs(type(realized[0]['lost']), int)
        # Decimal で計算するので 0.1 + 0.2 は 0.3 になります。
        self.assertIn(b'"gain":0.3,', self.get('?each=week').content)

    def test_non_numeric_user_id_returns_400(self):
        self.authorize()

        response = self.client.get('/api/v1/realized/abc/')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'')
        # each のチェックが先です。
        response = self.client.get('/api/v1/realized/abc/?each=decade')
        self.assertEqual(response.json(), {'message': "Invalid each query: 'decade'"})

    def test_invalid_each_returns_400(self):
        response = self.get('?each=decade')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'message': "Invalid each query: 'decade'"})
