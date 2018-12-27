"""
Example app URL configuration.
"""

from django.contrib import admin
from django.urls import path
from uniauth import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
]
