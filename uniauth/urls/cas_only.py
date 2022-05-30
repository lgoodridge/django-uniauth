try:
    from django.conf.urls import url
except ImportError:
    from django.urls import re_path as url
from django.core.exceptions import ImproperlyConfigured
from uniauth import views
from uniauth.utils import get_setting

# The standard login form requires URLs that don't exist when
# cas_only is used. Ensure that this setting is False.
if get_setting('UNIAUTH_LOGIN_DISPLAY_STANDARD'):
    err_msg = ("'uniauth.urls.cas_only' can not be used when %s is True. "
            "Please include 'uniauth.urls' instead.") % \
            'UNIAUTH_LOGIN_DISPLAY_STANDARD'
    raise ImproperlyConfigured(err_msg)

app_name = 'uniauth'

urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^cas-login/(?P<institution>[a-z0-9\-]+)/$', views.cas_login, name='cas-login'),
    url(r'^logout/$', views.logout, name='logout'),
]
