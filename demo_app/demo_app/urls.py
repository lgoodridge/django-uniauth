"""
Example app URL configuration.
"""

from django.contrib import admin
from django.conf.urls import include, url
from . import views

urlpatterns = [
    url('admin/', admin.site.urls),
    url('accounts/', include('uniauth.urls', namespace='uniauth')),
    url('^$', views.index, name='index'),
]
