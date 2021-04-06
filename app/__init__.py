
class Portfolio(object):
    """
    GET /api/v1/portfolio で返却する予定の model らしきものです。
    NOTE: GET /api/v1/portfolio を rest_framework で実装したいけれど、
          Model の無い ModelViewSet を実装する方法がわかりません。
          テキトーに {foo:foo} とかだけ出す API をどう作ればいいの?
          というわけでこちらの repository を参考にして実装しました。
          https://github.com/linovia/drf-demo
          Thank you.
    """

    def __init__(self, **kwargs):
        for field in ('id', 'foo', 'bar', 'baz'):
            setattr(self, field, kwargs.get(field, None))


class Realized(object):
    """
    GET /api/v1/realized で返却する予定の model らしきものです。
    NOTE: class Portfolio と同じ。
    """

    def __init__(self, **kwargs):
        for field in ('id', 'qux', 'quux'):
            setattr(self, field, kwargs.get(field, None))
