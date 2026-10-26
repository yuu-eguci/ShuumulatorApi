import datetime
import time
from decimal import Decimal

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.models import Stock, StockLog, Trading, User

# テスト専用のダミー値です。実際の秘密情報ではありません。
SYNTHETIC_SECRET_KEY = 'synthetic-test-secret-key-0123456789abcdefghijklmnopqrstuvwxyz'
SYNTHETIC_LOGIN_CODE = 'synthetic-login-code'


def utc(*args):
    return datetime.datetime(*args, tzinfo=datetime.UTC)


def make_token(user_id, expires_in=3600, key=None, **extra):
    payload = {'user_id': user_id, 'exp': int(time.time()) + expires_in, **extra}
    return jwt.encode(payload, key or settings.SECRET_KEY, algorithm='HS256')


@override_settings(SECRET_KEY=SYNTHETIC_SECRET_KEY, SHUUMULATOR_LOGIN_CODE=SYNTHETIC_LOGIN_CODE)
class ApiTestCase(TestCase):
    """ダミーの銘柄・ユーザー・取引を用意した TestCase です。"""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create(id=1, name='synthetic-user-1')
        cls.user2 = User.objects.create(id=2, name='synthetic-user-2')
        cls.stock_a = Stock.objects.create(code='1001', name='Synthetic A')
        cls.stock_b = Stock.objects.create(code='1002', name='Synthetic B')
        cls.stock_c = Stock.objects.create(code='1003', name='Synthetic C')

        # 確定済みの取引です。(buy, sell, sold_at)
        completed = [
            (cls.stock_a, '100.00', '150.00', utc(2020, 12, 30, 1)),
            (cls.stock_b, '200.00', '180.50', utc(2021, 1, 1, 2)),
            (cls.stock_a, '300.00', '330.25', utc(2021, 1, 4, 3)),
            (cls.stock_b, '400.00', '390.00', utc(2021, 1, 4, 5)),
            (cls.stock_a, '500.00', '500.00', utc(2021, 3, 31, 23, 30)),
            (cls.stock_b, '1.00', '1.10', utc(2021, 3, 31, 23, 40)),
            (cls.stock_a, '1.00', '1.20', utc(2021, 3, 31, 23, 50)),
        ]
        for stock, buy, sell, sold_at in completed:
            Trading.objects.create(
                stock=stock, user=cls.user1, buy=Decimal(buy), bought_at=sold_at - datetime.timedelta(days=1),
                sell=Decimal(sell), sold_at=sold_at,
            )

        # 保有中の取引です。
        Trading.objects.create(stock=cls.stock_a, user=cls.user1, buy=Decimal('120.00'), bought_at=utc(2021, 4, 1))
        Trading.objects.create(stock=cls.stock_c, user=cls.user1, buy=Decimal('50.00'), bought_at=utc(2021, 4, 2))

        # 別ユーザーの取引です。user1 のレスポンスに混ざってはいけません。
        Trading.objects.create(
            stock=cls.stock_a, user=cls.user2, buy=Decimal('1000.00'), bought_at=utc(2021, 1, 31),
            sell=Decimal('2000.00'), sold_at=utc(2021, 2, 1),
        )
        Trading.objects.create(stock=cls.stock_b, user=cls.user2, buy=Decimal('900.00'), bought_at=utc(2021, 2, 2))

        # 現在価格です。stock_c には価格がありません。
        StockLog.objects.create(stock=cls.stock_a, price=Decimal('125.00'))
        StockLog.objects.create(stock=cls.stock_b, price=Decimal('210.00'))

    def setUp(self):
        self.client = APIClient()

    def authorize(self, user_id=1, **kwargs):
        self.client.credentials(HTTP_AUTHORIZATION=f'JWT {make_token(user_id, **kwargs)}')
