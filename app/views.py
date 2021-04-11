from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from app.serializers import UserSerializer, PortfolioSerializer, RealizedSerializer
from django.views.decorators.csrf import requires_csrf_token
from django.http import (
    HttpResponseServerError,
)
from rest_framework.response import Response
from app.models import Trading, Stock, StockLog
import time

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

        try:

            # 手持ち stock(sell IS NULL)を取得するメソッドです。
            # NOTE: pk を user id として扱えばいいかな。
            keeping_tradings = fetch_keeping_tradings(pk)

            # NOTE: many=True をつけることで返却値が単一オブジェクトではなくリストになります。
            #       そのときは instance=[sample_portfolio] となる。
            #       retrieve は一件返却なので many=False
            #       def list のほうでは複数にするのだろう。
            # NOTE: Rest framework を使っているのに serializer を使っていません。
            #       今回は custom json を使うので別に要らないかなと。
            #       Rest framework の画面で返却値を見れるので、 Rest framework を使っているメリットはあります。
            #       まあ Rest framework 慣れてないから、とりあえずガシガシ実装するのが大事。
            return Response({
                'tradings': keeping_tradings,
            })

        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)


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


def fetch_keeping_tradings(user_id: int) -> list:
    """手持ちの stocks に情報をつけて返します。

    Args:
        user_id (int): Trading.user_id

    Returns:
        list: code, name, buy, bought_at, current_price をもつ dict のリスト
    """

    # NOTE: DB アクセスにどれくらい時間がかかるのか、なんとなく計測しています。
    start = time.time()

    # sell IS NULL を取得。
    # HACK: SELECT 項目を選びたいんだがやり方忘れた。たぶん values
    tradings = Trading.objects.filter(sell__isnull=True, user_id=user_id)

    # 各項目に、 stock_log.price を持たせます。(現在価格)
    # NOTE: 最新[stock レコード数]件が、最新の価格です。
    # NOTE: stock_log.is_newest とか足せばもっと明示的に書けると思う。
    stock_count = Stock.objects.count()
    stock_logs = StockLog.objects.order_by('id').reverse()[:stock_count]

    # 時間計測ログです。
    print(f'fetch_keeping_tradings(Trading, Stock, StockLog access finished): {time.time() - start}秒')

    # { stock_id: price } にフォーマット変更します。
    stock_log_dict = {}
    for stock_log in stock_logs:
        stock_log_dict[stock_log.stock.id] = stock_log.price

    # 返却する list を作成します。
    keeping_tradings = []
    for trading in tradings:
        keeping_tradings.append({
            'code': trading.stock.code,
            'name': trading.stock.name,
            'buy': trading.buy,
            'bought_at': trading.bought_at,
            'current_price': stock_log_dict[trading.stock.id] if trading.stock.id in stock_log_dict else None,
        })

    return keeping_tradings


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
