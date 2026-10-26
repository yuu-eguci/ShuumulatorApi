from django.db.models import OuterRef, Subquery
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from app.auth import JWTAuthentication, NormalAuthentication
from app.models import StockLog, Trading
from app.serializers import PortfolioSerializer, RealizedSerializer


def parse_user_id(pk):
    """URL の user_id を数値にします。数値でなければ None です。"""
    try:
        return int(pk)
    except (TypeError, ValueError):
        return None


def check_owner(request, user_id):
    """自分以外の user_id のデータは見せません。"""
    if user_id != request.user.id:
        raise PermissionDenied()


class UserViewSet(viewsets.ViewSet):
    """
    API endpoint that checks whether the JWT is valid.
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
        # NOTE: 以前は ModelViewSet で、使っていない list などを呼ぶと 500 になっていました。

        return Response({
            'hello': True,
        }, status=status.HTTP_200_OK)


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

        # NOTE: pk を user id として扱います。数値でなければ 2021 年版と同じく 400 です。
        user_id = parse_user_id(pk)
        if user_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        check_owner(request, user_id)

        # 手持ち stock(sell IS NULL)を取得するメソッドです。
        # NOTE: Rest framework を使っているのに serializer を使っていません。
        #       今回は custom json を使うので別に要らないかなと。
        return Response({
            'tradings': fetch_keeping_tradings(user_id),
        })


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

        # 引数 each の isIn チェックです。
        each = request.GET.get(key='each', default='year')
        if each not in ['year', 'month', 'week', 'day']:
            return Response(
                {
                    'message': f"Invalid each query: '{each}'",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # NOTE: pk を user id として扱います。数値でなければ 2021 年版と同じく 400 です。
        user_id = parse_user_id(pk)
        if user_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        check_owner(request, user_id)

        # 完了済みの Tradings を取得します。
        completed_tradings = fetch_completed_tradings(user_id)

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
    # 完了した取引が無いときは 0 です。
    win_rate = win / (win + lose) if win + lose else 0
    return win_rate, total_gain, total_lost


def fetch_completed_tradings(user_id):

    # 完了した Tradings を収集します。
    # NOTE: 完了は sell IS NOT NULL です。 buy や sold_at が無いものは損益を計算できないので除きます。
    return list(
        Trading.objects
        .filter(user_id=user_id, sell__isnull=False, buy__isnull=False, sold_at__isnull=False)
        .order_by('sold_at', 'id')
        .values('buy', 'sell', 'sold_at')
    )


def labels_of(sold_at):
    """「年」「月」「週」「日」の label を作ります。

    NOTE: 2021 年版は pandas で作っていた label をそのまま再現しています。
          week は月の label に ISO 週番号を、 day は week の label に日を足したものです。
    """
    year = str(sold_at.year)
    month = f'{year}-{sold_at.month}'
    week = f'{month}-{sold_at.isocalendar()[1]}'
    day = f'{week}-{sold_at.day}'
    return {'year': year, 'month': month, 'week': week, 'day': day}


def divide_tradings(tradings, each):

    # each 引数に従って realized リストを作ります。
    # NOTE: year(default) -> 年ごとに gain, lost を集計。
    #       month -> 月ごとに集計。
    #       week -> 週ごとに集計。
    #       day -> 日ごとに集計。
    divided = []
    used_value = []
    for trading in tradings:
        row = {**trading, **labels_of(trading['sold_at']), 'realized': trading['sell'] - trading['buy']}
        # 属性の値が変わったタイミングで新しいグループ(list)を作る。
        if row[each] not in used_value:
            divided.append([])
            used_value.append(row[each])
        # row は一番新しいグループに入れる。
        divided[-1].append(row)

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
        realized_list.append({'gain': gain, 'lost': lost, 'label': label})
    return realized_list


def fetch_keeping_tradings(user_id) -> list:
    """手持ちの stocks に情報をつけて返します。

    Args:
        user_id (int): Trading.user_id

    Returns:
        list: code, name, buy, bought_at, current_price をもつ dict のリスト
    """

    # 銘柄ごとの最新の stock_log.price が現在価格です。
    # NOTE: 以前は「最新[stock レコード数]件」を現在価格にしていて、銘柄ごとの記録回数がずれると古い価格になっていました。
    latest_price = StockLog.objects.filter(stock=OuterRef('stock')).order_by('-id').values('price')[:1]

    # sell IS NULL を取得。
    tradings = (
        Trading.objects
        .filter(sell__isnull=True, user_id=user_id)
        .select_related('stock')
        .annotate(current_price=Subquery(latest_price))
        .order_by('id')
    )

    return [
        {
            'code': trading.stock.code,
            'name': trading.stock.name,
            'buy': trading.buy,
            'bought_at': trading.bought_at,
            'current_price': trading.current_price,
        }
        for trading in tradings
    ]


class Login(APIView):
    """このクラスにより、次のことが可能になった。
    - path('api-token-auth/', views.Login.as_view())
    - POST {"code": "..."} すると jwt が返ってくる。(def post の効果)
    - authentication_classes = [JWTAuthentication] と permission_classes = [permissions.IsAuthenticated] をつけた
      viewset には、その token を付与しとかないとアクセスできない
    """

    authentication_classes = [NormalAuthentication]

    def post(self, request, *args, **kwargs):
        return Response({'token': request.user})
