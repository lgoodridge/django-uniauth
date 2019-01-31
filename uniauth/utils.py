from django.conf import settings
from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.six.moves import urllib_parse


# The default value for all settings used by Uniauth
DEFAULT_SETTING_VALUES = {
    'LOGIN_URL': '/accounts/login/',
    'PASSWORD_RESET_TIMEOUT_DAYS': 3,
    'UNIAUTH_ALLOW_STANDALONE_ACCOUNTS': True,
    'UNIAUTH_FROM_EMAIL': 'uniauth@example.com',
    'UNIAUTH_LOGIN_REDIRECT_URL': '/',
    'UNIAUTH_LOGOUT_REDIRECT_URL': None,
    'UNIAUTH_LOGOUT_CAS_COMPLETELY': False,
}


def choose_username(email):
    """
    Chooses a unique username for the provided user.

    Sets the username to the email parameter umodified if
    possible, otherwise adds a numerical suffix to the email.
    """
    def get_suffix(number):
        return "" if number == 1 else "_"+str(number).zfill(3)
    user_model = get_user_model()
    num = 1
    while user_model.objects.filter(username=email+get_suffix(num)).exists():
        num += 1
    return email + get_suffix(num)


def get_protocol(request):
    """
    Returns the protocol request is using ('http' | 'https')
    """
    return 'https' if request.is_secure() else 'http'


def get_random_username():
    """
    Returns a username generated from current timestamp + random string
    """
    return "tmp-%s_%s" % (timezone.now().strftime("%Y%m%d%H%M%S%f"),
            get_random_string(5))


def get_redirect_url(request, use_referer=False, default_url=None):
    """
    Returns the URL to redirect to once business at the current
    URL is completed.

    Picks the first usable URL from the following list:
      1. URL provided as GET parameter under REDIRECT_FIELD_NAME
      2. Referring page if use_referer is True, and set in header
      3. default_url parameter
      4. UNIAUTH_LOGIN_REDIRECT_URL setting
    """
    redirect_url = request.GET.get(REDIRECT_FIELD_NAME)
    if not redirect_url:
        if use_referer:
            redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = resolve_url(default_url or
                    get_setting('UNIAUTH_LOGIN_REDIRECT_URL'))
        prefix = urllib_parse.urlunparse(
                (get_protocol(request), request.get_host(), '', '', '', ''),
        )
        if redirect_url.startswith(prefix):
            redirect_url = redirect_url[len(prefix):]
    return redirect_url


def get_service_url(request, redirect_url=None):
    """
    Returns the service URL to provide to the CAS
    server for the provided request.

    Accepts an optional redirect_url, which defaults
    to the value of get_redirect_url(request).
    """
    service_url = urllib_parse.urlunparse(
            (get_protocol(request), request.get_host(),
            request.path, '', '', ''),
    )
    service_url += ('&' if '?' in service_url else '?')
    service_url += urllib_parse.urlencode({
            REDIRECT_FIELD_NAME: redirect_url or get_redirect_url(request)
    })
    return service_url


def get_setting(setting_name):
    """
    Returns the value of the setting with the provided name
    if set. Returns the value in DEFAULT_SETTING_VALUES
    otherwise.
    """
    try:
        return getattr(settings, setting_name)
    except AttributeError:
        return DEFAULT_SETTING_VALUES[setting_name]


def is_tmp_user(user):
    """
    Returns whether the provided user is a temporary one:

    By default, this includes users midway through verifying
    their profile (have usernames starting with "tmp").

    If the UNIAUTH_ALLOW_STANDALONE_ACCOUNTS setting is
    False, it includes Institution Account logins (such as
    CAS) that have not been linked to a Uniauth profile yet.
    """
    return user.username and (user.username.startswith('tmp-') or \
            (not get_setting('UNIAUTH_ALLOW_STANDALONE_ACCOUNTS') and \
                    is_unlinked_account(user)))


def is_unlinked_account(user):
    """
    Returns whether the provided user has authenticated via
    an InstitutionAccount not yet linked to a Uniauth profile.
    """
    return user.username and user.username.startswith('cas-')
