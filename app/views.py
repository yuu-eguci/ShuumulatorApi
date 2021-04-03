from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from app.serializers import UserSerializer
from django.views.decorators.csrf import requires_csrf_token
from django.http import (
    HttpResponseServerError,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


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
