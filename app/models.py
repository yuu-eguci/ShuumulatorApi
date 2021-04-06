from django.db import models


class Stock(models.Model):

    code = models.CharField(
        verbose_name='銘柄コード',
        unique=True,
        # NOTE: CharField の必須引数です。
        max_length=45,
        null=False,
    )
    name = models.CharField(
        verbose_name='銘柄名',
        unique=False,
        # NOTE: CharField の必須引数です。
        max_length=45,
        null=False,
    )

    class Meta:

        # NOTE: 本プロジェクトは DB 構造先行です。
        #       そのため DB 名は Django に決めさせず、手動で指定します。
        db_table = 'stock'


class StockLog(models.Model):

    stock = models.ForeignKey(
        Stock,
        verbose_name='銘柄',
        null=False,
        # NOTE: ForeignKey の positional argument.
        on_delete=models.PROTECT,
    )
    price = models.DecimalField(
        verbose_name='価格',
        null=False,
        # NOTE: Decimal(6, 2) です。
        max_digits=8,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        verbose_name='作成時刻',
        null=False,
        auto_now_add=True,
    )

    class Meta:

        # NOTE: 本プロジェクトは DB 構造先行です。
        #       そのため DB 名は Django に決めさせず、手動で指定します。
        db_table = 'stock_log'


class User(models.Model):

    name = models.CharField(
        verbose_name='名称',
        null=False,
        # NOTE: CharField の必須引数です。
        max_length=45,
    )

    class Meta:

        # NOTE: 本プロジェクトは DB 構造先行です。
        #       そのため DB 名は Django に決めさせず、手動で指定します。
        db_table = 'user'


class Trading(models.Model):

    stock = models.ForeignKey(
        Stock,
        verbose_name='銘柄',
        null=False,
        # NOTE: ForeignKey の positional argument.
        on_delete=models.PROTECT,
    )
    user = models.ForeignKey(
        User,
        verbose_name='ユーザ',
        null=False,
        # NOTE: ForeignKey の positional argument.
        on_delete=models.PROTECT,
    )
    buy = models.DecimalField(
        verbose_name='買付価格',
        # NOTE: なんとなく売付価格と同じく null 許可にしてしまいました。
        # NOTE: Decimal(6, 2) です。
        max_digits=8,
        decimal_places=2,
        null=True,
    )
    bought_at = models.DateTimeField(
        verbose_name='買付時刻',
        # NOTE: なんとなく売付価格と同じく null 許可にしてしまいました。
        null=True,
    )
    sell = models.DecimalField(
        verbose_name='売付価格',
        # NOTE: 買付時には売付価格はわかりません。 null 許可は当然です。
        # NOTE: Decimal(6, 2) です。
        max_digits=8,
        decimal_places=2,
        null=True,
    )
    sold_at = models.DateTimeField(
        verbose_name='売付時刻',
        # NOTE: 買付時には売付時刻はわかりません。 null 許可は当然です。
        null=True,
    )
    created_at = models.DateTimeField(
        verbose_name='作成時刻',
        null=False,
        auto_now_add=True,
    )

    class Meta:

        # NOTE: 本プロジェクトは DB 構造先行です。
        #       そのため DB 名は Django に決めさせず、手動で指定します。
        db_table = 'trading'
