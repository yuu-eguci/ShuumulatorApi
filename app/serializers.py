from rest_framework import serializers


class PortfolioSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    foo = serializers.CharField(max_length=256)
    bar = serializers.CharField(max_length=256)
    baz = serializers.CharField(max_length=256)


class RealizedSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    qux = serializers.CharField(max_length=256)
    quux = serializers.CharField(max_length=256)
