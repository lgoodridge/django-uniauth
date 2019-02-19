"""
URL configuration for testing.
"""

from django.conf.urls import include, url

urlpatterns = [
    url('accounts/', include('uniauth.urls', namespace='uniauth')),
]
