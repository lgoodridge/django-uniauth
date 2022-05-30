"""
URL configuration for testing.
"""

try:
    from django.conf.urls import include, url
except ImportError:
    from django.urls import include, re_path as url

urlpatterns = [
    url('accounts/', include('uniauth.urls', namespace='uniauth')),
]
