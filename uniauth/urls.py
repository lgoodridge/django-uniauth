from django.conf.urls import url
from uniauth import views

app_name = 'uniauth'

urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^cas-login/(?P<institution>[a-z0-9]+)/$', views.cas_login, name='cas-login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^link-to-account/$', views.link_to_account, name='link-to-account'),
    url(r'^link-from-account/(?P<institution>[a-z0-9]+)/$', views.link_from_account, name='link-from-account'),
    url(r'^verify-token/(?P<pk_base64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.verify_token, name='verify-token'),
    url(r'^password-reset/', views.PasswordReset.as_view(), name='password-reset'),
    url(r'^password-reset-done/', views.PasswordResetDone.as_view(), name='password-reset-done'),
    url(r'^password-reset-verify/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/', views.PasswordResetVerify.as_view(), name='password-reset-verify'),
    url(r'^password-reset-verify-done/', views.PasswordResetVerifyDone.as_view(), name='password-reset-verify-done'),
]
