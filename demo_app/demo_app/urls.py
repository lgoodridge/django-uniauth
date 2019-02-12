"""
Example app URL configuration.
"""

from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('uniauth.urls', namespace='uniauth')),
    path('', views.index, name='index'),
]
