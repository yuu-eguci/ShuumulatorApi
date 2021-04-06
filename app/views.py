from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from app.serializers import UserSerializer, PortfolioSerializer, RealizedSerializer
from django.views.decorators.csrf import requires_csrf_token
from django.http import (
    HttpResponseServerError,
)
from rest_framework.response import Response

# __init__.py に定義しているクラスです。
from . import Portfolio, Realized


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class PortfolioViewSet(viewsets.ViewSet):
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = PortfolioSerializer

    def list(self, request):
        # NOTE: 今回は list は不要だが、これがないとトップページの API リストにこの ViewSet が載らない。
        serializer = PortfolioSerializer(instance=[], many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        # NOTE: pk を user id として扱えばいいかな。
        sample_portfolio = Portfolio(
            id=123,
            foo='FOOOO',
            bar='BAAAR',
            baz='BAAAZ',
        )
        try:
            # NOTE: 本来ならここで一件取得するらしい。
            # task = tasks[int(pk)]
            pass
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # NOTE: many=True をつけることで返却値が単一オブジェクトではなくリストになります。
        #       そのときは instance=[sample_portfolio] となる。
        #       retrieve は一件返却なので many=False
        #       def list のほうでは複数にするのだろう。
        serializer = PortfolioSerializer(instance=sample_portfolio)
        return Response(serializer.data)


class RealizedViewSet(viewsets.ViewSet):
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = RealizedSerializer

    def list(self, request):
        # NOTE: 今回は list は不要だが、これがないとトップページの API リストにこの ViewSet が載らない。
        serializer = RealizedSerializer(instance=[], many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        # NOTE: pk を user id として扱えばいいかな。
        sample_realized = Realized(
            id=123,
            qux='QUX',
            quux='QUUX',
        )
        try:
            # NOTE: 本来ならここで一件取得するらしい。
            # task = tasks[int(pk)]
            pass
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # NOTE: many=True をつけることで返却値が単一オブジェクトではなくリストになります。
        #       そのときは instance=[sample_realized] となる。
        #       retrieve は一件返却なので many=False
        #       def list のほうでは複数にするのだろう。
        serializer = RealizedSerializer(instance=sample_realized)
        return Response(serializer.data)


@requires_csrf_token
def my_customized_server_error(request, template_name='500.html'):

    # NOTE: print が App Service で機能するかどうか確かめるために print しています。
    import traceback
    print(traceback.format_exc())
    # return HttpResponseServerError('<h1>Server Error (500)</h1>')

    # DEBUG = True と同様の画面を出します。
    import sys
    from django.views import debug
    error_html = debug.technical_500_response(request, *sys.exc_info()).content
    return HttpResponseServerError(error_html)
