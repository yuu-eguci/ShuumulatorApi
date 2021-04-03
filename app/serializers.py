from django.contrib.auth.models import User, Group
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """最初からある User モデル。そのための serializer です。"""

    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']
