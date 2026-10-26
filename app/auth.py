import hmac
import time

import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from app.models import User

# ログインで発行するトークンの持ち主です。本プロジェクトはユーザー 1 人で遊ぶ前提です。
LOGIN_USER_ID = 1


def generate_jwt(user_object):

    # 期限、1h
    timestamp = int(time.time()) + 60 * 60

    return jwt.encode({
        'user_id': user_object.id,
        'exp': timestamp,
    }, settings.SECRET_KEY, algorithm='HS256')


class NormalAuthentication(BaseAuthentication):
    def authenticate(self, request):

        # NOTE: JSON として読めない body は request.data が ParseError (400) を返します。
        data = request.data
        code = data.get('code') if isinstance(data, dict) else None
        expected = settings.SHUUMULATOR_LOGIN_CODE

        # ログイン用コードは環境変数から読み、定数時間で比較します。
        if isinstance(code, str) and expected and hmac.compare_digest(code.encode(), expected.encode()):
            user_object = User.objects.filter(id=LOGIN_USER_ID).first()
            if user_object is not None:
                # NOTE: ここで return jwt としていたせいで
                #       ValueError: too many values to unpack (expected 2)
                #       が出た。
                return generate_jwt(user_object), None

        # NOTE: 失敗したとき {"detail":"Authentication failed!!!"} こうなる。
        raise exceptions.AuthenticationFailed('Authentication failed!!!')

    def authenticate_header(self, request):
        # NOTE: None を返すので認証失敗は 401 ではなく 403 になります。
        pass


class JWTAuthentication(BaseAuthentication):
    keyword = 'JWT'
    model = None

    def authenticate(self, request):

        # なぜか request.user を参照すると maximum recursion depth exceeded while calling a Python object 発生するイミフ
        # NOTE: authenticate の中で request.user を読むと、この authenticate がまた呼ばれるためです。

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = "Authorization 無効"
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = "Authorization 無効 スペースはない"
            raise exceptions.AuthenticationFailed(msg)

        jwt_token = auth[1]
        try:
            # NOTE: 参考にしたコードには algorithms はなかったが、
            #       v2.0.0 から必須になったみたい。
            #       https://github.com/jpadilla/pyjwt/blob/master/CHANGELOG.rst#dropped-deprecated-verify-param-in-jwtdecode
            jwt_info = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=['HS256'], options={'require': ['exp']})
        except jwt.ExpiredSignatureError:
            msg = "tokenはtimeout"
            raise exceptions.AuthenticationFailed(msg) from None
        except jwt.InvalidSignatureError:
            msg = "InvalidSignatureError"
            raise exceptions.AuthenticationFailed(msg) from None
        except jwt.InvalidTokenError:
            msg = "Authorization 無効"
            raise exceptions.AuthenticationFailed(msg) from None

        user_id = jwt_info.get("user_id")
        if not isinstance(user_id, int):
            msg = "ユーザー存在しません"
            raise exceptions.AuthenticationFailed(msg)
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            msg = "ユーザー存在しません"
            raise exceptions.AuthenticationFailed(msg)
        user.is_authenticated = True
        return (user, jwt_token)

    def authenticate_header(self, request):
        pass
