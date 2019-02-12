"""
URL configuration for testing.
"""

from django.urls import include, path

urlpatterns = [
    path('accounts/', include('uniauth.urls', namespace='uniauth')),
]
