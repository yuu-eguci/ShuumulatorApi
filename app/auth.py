import time
import jwt
from config.settings import SECRET_KEY
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from app.models import User
from rest_framework.authentication import get_authorization_header


def generate_jwt(user_object):

    # 期限、1h
    timestamp = int(time.time()) + 60 * 60

    print('generate_jwt')

    return jwt.encode({
        'user_id': user_object.id,
        'exp': timestamp,
    }, SECRET_KEY)


class NormalAuthentication(BaseAuthentication):
    def authenticate(self, request):

        # 今回は遊びなのでベタ書き。
        print('NormalAuthentication.authenticate!!!', request.POST, request.POST.get('code'))
        if request._request.POST.get('code') == 'everybody-dance-now':
            user_object = User.objects.filter(id=1)[0]
            print('user_object', user_object)
            jwt = generate_jwt(user_object)
            print(dict(jwt=jwt))
            # NOTE: ここで return jwt としていたせいで
            #       ValueError: too many values to unpack (expected 2)
            #       が出た。
            return jwt, None

        # NOTE: 失敗したとき {"detail":"Authentication failed!!!"} こうなる。
        raise exceptions.AuthenticationFailed('Authentication failed!!!')

    def authenticate_header(self, request):
        pass


class JWTAuthentication(BaseAuthentication):
    keyword = 'JWT'
    model = None

    def authenticate(self, request):

        print('JWTAuthentication.authenticate~!!!!')

        # なぜか request.user を参照すると maximum recursion depth exceeded while calling a Python object 発生するイミフ
        # print(request.user)

        auth = get_authorization_header(request).split()
        print(dict(auth=auth))

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = "Authorization 無効"
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = "Authorization 無効 スペースはない"
            raise exceptions.AuthenticationFailed(msg)

        try:
            jwt_token = auth[1]
            # NOTE: 参考にしたコードには algorithms はなかったが、
            #       v2.0.0 から必須になったみたい。
            #       https://github.com/jpadilla/pyjwt/blob/master/CHANGELOG.rst#dropped-deprecated-verify-param-in-jwtdecode
            jwt_info = jwt.decode(jwt_token, SECRET_KEY, algorithms=['HS256'])
            user_id = jwt_info.get("user_id")
            try:
                user = User.objects.get(pk=user_id)
                user.is_authenticated = True
                return (user, jwt_token)
            except:
                msg = "ユーザー存在しません"
                raise exceptions.AuthenticationFailed(msg)
        except jwt.ExpiredSignatureError:
            msg = "tokenはtimeout"
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidSignatureError:
            msg = "InvalidSignatureError"
            raise exceptions.AuthenticationFailed(msg)

    def authenticate_header(self, request):
        pass
