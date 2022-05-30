try:
    from django.conf.urls import url
except ImportError:
    from django.urls import re_path as url
from uniauth import views

app_name = 'uniauth'

urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^cas-login/(?P<institution>[a-z0-9\-]+)/$', views.cas_login, name='cas-login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^link-to-profile/$', views.link_to_profile, name='link-to-profile'),
    url(r'^link-from-profile/(?P<institution>[a-z0-9\-]+)/$', views.link_from_profile, name='link-from-profile'),
    url(r'^verify-token/(?P<pk_base64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$', views.verify_token, name='verify-token'),
    url(r'^password-reset/', views.PasswordReset.as_view(), name='password-reset'),
    url(r'^password-reset-done/', views.PasswordResetDone.as_view(), name='password-reset-done'),
    url(r'^password-reset-verify/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/', views.PasswordResetVerify.as_view(), name='password-reset-verify'),
    url(r'^password-reset-verify-done/', views.PasswordResetVerifyDone.as_view(), name='password-reset-verify-done'),
    url(r'^jwt-tokens/', views.get_jwt_tokens_from_session, name="jwt-tokens")
]
