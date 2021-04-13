from django.contrib.auth.models import User, Group
from rest_framework import viewsets, permissions, status
from app.serializers import UserSerializer, PortfolioSerializer, RealizedSerializer
from django.views.decorators.csrf import requires_csrf_token
from django.http import (
    HttpResponseServerError,
)
from rest_framework.response import Response
from app.models import Trading, Stock, StockLog
import time
from django_pandas.io import read_frame
from rest_framework.views import APIView
from app.auth import NormalAuthentication, JWTAuthentication

# __init__.py に定義しているクラスです。
from . import Portfolio, Realized


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    # JWT ログインしているユーザのみ許可する設定です。
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def retrieve(self, request, pk=None):

        # NOTE: この retrieve は、ただのアクセス者がログインしているかどうかチェックするためだけに追加した。
        #       「jwt でログインチェックってどうすりゃいいんだ?」
        #       ↓
        #       「authentication_classes = [JWTAuthentication] をつけた ViewSet で200返すだけでいいんじゃない?」
        #       ↓
        #       「retrieve にしたら url が /user/:pk になるじゃん。 pk 要らないんだけど」
        #       ↓
        #       「まあいっかお試しだしざくざく実装しよ」
        #       ↓
        #       ↓

        print('UserViewSet.retrieve!!!')

        return Response({
            'hello': True,
        },status=status.HTTP_200_OK)


class PortfolioViewSet(viewsets.ViewSet):

    # JWT ログインしているユーザのみ許可する設定です。
    authentication_classes = [JWTAuthentication]
    # NOTE: これは and なのか or なのかそれが問題だ。 -> and らしい。
    #       https://stackoverflow.com/questions/35557156/how-to-get-or-permissions-instead-of-and-in-rest-framework
    permission_classes = [permissions.IsAuthenticated]

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

    # JWT ログインしているユーザのみ許可する設定です。
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # Required for the Browsable API renderer to have a nice form.
    serializer_class = RealizedSerializer

    def list(self, request):
        # NOTE: 今回は list は不要だが、これがないとトップページの API リストにこの ViewSet が載らない。
        serializer = RealizedSerializer(instance=[], many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):

        try:

            # 引数 each の isIn チェックです。
            each = request.GET.get(key='each', default='year')
            if each not in ['year', 'month', 'week', 'day']:
                return Response(
                    {
                        'message': f"Invalid each query: '{each}'",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 完了済みの Tradings を取得します。
            completed_tradings = fetch_completed_tradings(pk, each)

            # realized 返却を行うため、以下で分割とかするけど、トータルの gain や lost、 win rate もほしいので先に集計しておきます。
            win_rate, total_gain, total_lost = aggregate_totals(completed_tradings)

            # each 引数で指定された単位ごとに分割します。
            divided_tradings = divide_tradings(completed_tradings, each)

            # 分割してもらったけれど、必要なのは単位ごとに分けられた各グループの集計結果だけです。
            realized_list = aggregate_tradings(divided_tradings, each)

            return Response({
                'user_id': pk,
                'each': each,
                'realized': realized_list,
                'win_rate': win_rate,
                'total_gain': total_gain,
                'total_lost': total_lost,
            })

        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)


def aggregate_totals(tradings):

    win = 0
    lose = 0
    total_gain = 0
    total_lost = 0
    for trading in tradings:
        realized = trading['sell'] - trading['buy']
        if realized >= 0:
            win += 1
            total_gain += realized
        else:
            lose += 1
            total_lost += -realized
    win_rate = win / (win + lose)
    return win_rate, total_gain, total_lost


def fetch_completed_tradings(user_id: int, each: str):

    # NOTE: DB アクセスにどれくらい時間がかかるのか、なんとなく計測しています。
    start = time.time()

    # 完了した Tradings を収集します。
    # NOTE: 完了は sell IS NOT NULL です。
    completed_tradings = Trading.objects.filter(sell__isnull=False, user_id=user_id).values('stock', 'buy', 'sell', 'sold_at')

    # 時間計測ログです。
    print(f'fetch_completed_trading(Trading access finished): {time.time() - start}秒')

    return completed_tradings


def divide_tradings(tradings, each):

    # each 引数に従って realized リストを作ります。
    # NOTE: year(default) -> 年ごとに gain, lost を集計。
    #       month -> 月ごとに集計。
    #       week -> 週ごとに集計。
    #       day -> 日ごとに集計。

    # NOTE: django_pandas.io.read_frame です。
    # NOTE: pandas を使うと、各行に「年」「月」「週」「日」属性をかんたんにつけられそうだったので、使います。
    data_frame = read_frame(tradings)

    # 各行に「年」「月」「週」「日」属性を付与します。
    # NOTE: これら属性には、 dt.*** の返却値の合計が入ります。値自体は無意味だけど、各単位ごとに一意になるってこと。うまく説明できねえ。
    # NOTE: each ごとに必要な属性が違うので、指定された each 以外の3つの属性は無駄ですが、 if が多くなって面倒なので一括で付与します。
    data_frame['year'] = data_frame['sold_at'].dt.year.astype(str)
    data_frame['month'] = data_frame['year'] + '-' + data_frame['sold_at'].dt.month.astype(str)
    data_frame['week'] = data_frame['month'] + '-' + data_frame['sold_at'].dt.isocalendar().week.astype(str)
    data_frame['day'] = data_frame['week'] + '-' + data_frame['sold_at'].dt.day.astype(str)

    # どうせ data frame に行を足すならば、 realized 列も足してしまえ。
    data_frame['realized'] = data_frame['sell'] - data_frame['buy']

    # NOTE: こんな data_frame になっています。
    #                  stock      buy     sell                          sold_at  year   month       week          day realized
    # 0     Stock object (1)  1443.00  1399.00        2021-03-05 03:04:02+00:00  2021  2021-3   2021-3-9   2021-3-9-5   -44.00
    # 1     Stock object (2)  1677.00  1624.00        2021-03-03 01:37:14+00:00  2021  2021-3   2021-3-9   2021-3-9-3   -53.00
    # ..                 ...      ...      ...                              ...   ...     ...        ...          ...      ...
    # 421  Stock object (40)   355.00   311.00 2021-04-08 06:26:59.236529+00:00  2021  2021-4  2021-4-14  2021-4-14-8   -44.00
    # 422  Stock object (29)  1282.00  1160.00 2021-04-09 01:25:29.109191+00:00  2021  2021-4  2021-4-14  2021-4-14-9  -122.00

    # each 引数ごとに分けます。
    # NOTE: each=year なら data_frame[year] の値ごとに分ければいいということ。
    divided = []
    # NOTE: data_frame をそのまま for すると column 取得になる。びっくり。
    used_value = []
    for index, row in data_frame.iterrows():
        # 属性の値が変わったタイミングで新しいグループ(list)を作る。
        if row[each] not in used_value:
            divided.append([])
            used_value.append(row[each])
        # row は一番新しいグループに入れる。
        # NOTE: pandas の概念は本関数内で完結させるため、 dict で返します。
        divided[-1].append(dict(row))

    return divided


def aggregate_tradings(divided_tradings, each):

    # こういうリストになっています。
    # [[Trading list], [Trading list], ]
    # 各 Trading list を { label, gain, lost } の情報にまとめます。
    realized_list = []
    for trading_list in divided_tradings:
        gain = 0
        lost = 0
        for trading in trading_list:
            if trading['realized'] >= 0:
                gain += trading['realized']
            else:
                # 正の数で合計したいので、マイナスをつけます。
                lost += -trading['realized']
        # ラベルをつけます。 each 単位によって違います。
        # NOTE: year なら year だけでいいし、 month なら month まで欲しい。
        label = trading_list[0][each]
        realized_list.append(dict(gain=gain, lost=lost, label=label))
    return realized_list


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


class Login(APIView):
    """このクラスにより、次のことが可能になった。
    - path('api-token-auth/', views.Login.as_view())
    - curl -X POST -d "code=everybody-dance-now" http://localhost:8000/api-token-auth/ こんなふうにアクセスすると jwt が返ってくる。(def post の効果)
    - authentication_classes = [JWTAuthentication] と permission_classes = [permissions.IsAuthenticated] をつけた viewset には、その token を付与しとかないとアクセスできない

    Args:
        APIView ([type]): [description]

    Returns:
        [type]: [description]
    """

    authentication_classes = [NormalAuthentication]

    def post(self, request, *args, **kwargs):
        print('Login.post!!', request.POST)
        return Response({'token': request.user})
