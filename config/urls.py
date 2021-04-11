"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from app import views
from rest_framework.routers import DefaultRouter

# Create a router and register our viewsets with it.
# NOTE: viewsets とやらは views.py で定義する。
router = DefaultRouter()
# r'api/v1/users' にすればその URL でアクセスできる。
router.register(r'users', views.UserViewSet)
# NOTE: The base to use for the URL names that are created.
#       (って書いてあるけど URL になるのは第一引数だ。どゆこと?)
#       If unset the basename will be automatically generated based on the queryset attribute of the viewset, if it has one.
#       Note that if the viewset does not include a queryset attribute
#       then you must set basename when registering the viewset.
#       (portfolio は non model API なので、 queryset が無い。わざわざ定義する必要がある。)
# NOTE: でも上述したとおり URL になるのは第一引数だ。なんのために basename を定義してるのかわからん。
#       それを表すため、意味のない値 foo を設定しています。
router.register(r'api/v1/portfolio', views.PortfolioViewSet, basename='foo')
router.register(r'api/v1/realized', views.RealizedViewSet, basename='bar')

urlpatterns = [
    # Django 本来のアドミン画面。
    path('admin/', admin.site.urls),
    # トップ画面を REST framework にする。
    path('', include(router.urls)),
    # NOTE: api-auth/ を追加することで画面に login のリンクが出る。
    # NOTE: 今回は jwt の認証をつかうので不要。
    #       -> Superuser アクセスも可能にしたほうがテストしやすいと思ったので再有効化。
    path('api-auth/',
         include('rest_framework.urls',
                 namespace='rest_framework'),
         ),
    # NOTE: ViewSet を使って↑のように書くことで、こういうのが全部省略できる。
    # path('users/', user_list, name='user-list'),
    # path('users/<int:pk>/', user_detail, name='user-detail'),

    path('api-token-auth/', views.Login.as_view()),
]

handler500 = views.my_customized_server_error
