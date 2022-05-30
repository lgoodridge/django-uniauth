from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_str as force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
try:
    from urllib import urlencode
    from urlparse import urlunparse
except ImportError:
    from urllib.parse import urlencode, urlunparse


# The default value for all settings used by Uniauth
DEFAULT_SETTING_VALUES = {
    'LOGIN_URL': '/accounts/login/',
    'PASSWORD_RESET_TIMEOUT_DAYS': 3,
    'UNIAUTH_ALLOW_STANDALONE_ACCOUNTS': True,
    'UNIAUTH_ALLOW_SHARED_EMAILS': True,
    'UNIAUTH_FROM_EMAIL': 'uniauth@example.com',
    'UNIAUTH_LOGIN_DISPLAY_STANDARD': True,
    'UNIAUTH_LOGIN_DISPLAY_CAS': True,
    'UNIAUTH_LOGIN_REDIRECT_URL': '/',
    'UNIAUTH_LOGOUT_CAS_COMPLETELY': False,
    'UNIAUTH_LOGOUT_REDIRECT_URL': None,
    'UNIAUTH_MAX_LINKED_EMAILS': 20,
    'UNIAUTH_PERFORM_RECURSIVE_MERGING': True,
    'UNIAUTH_USE_JWT_AUTH': False
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


def decode_pk(encoded_pk):
    """
    Decodes the provided base64 encoded pk into its
    original value, as a string
    """
    return force_text(urlsafe_base64_decode(encoded_pk))


def encode_pk(pk):
    """
    Returns the base64 encoding of the provided pk
    """
    encoded = urlsafe_base64_encode(force_bytes(pk))
    # On Django <2.1, this method returns a byte string
    try:
        encoded = encoded.decode()
    except AttributeError:
        pass
    return encoded


def flush_old_tmp_users(days=1):
    """
    Delete temporary users more than the specified number of days old.

    Returns the number of users deleted by this action.
    """
    user_model = get_user_model()
    old_tmp_users = user_model.objects.filter(
        username__startswith="tmp-",
        date_joined__lte=timezone.now()-timedelta(days=days)
    )
    num_deleted = old_tmp_users.count()
    old_tmp_users.delete()
    return num_deleted


def get_account_username_split(username):
    """
    Accepts the username for an unlinked InstitutionAccount
    and return a tuple containing the following:
      0: Account Type (e.g. 'cas')
      1: Institution Slug
      2: User ID for the institution
    """
    username_split = username.split("-")
    if len(username_split) < 3:
        raise ValueError("Value passed to get_account_username_split " +
                "was not the username for an unlinked InstitutionAccount.")
    slug = "-".join(username_split[1:len(username_split)-1])
    return (username_split[0], slug, username_split[len(username_split)-1])


def get_input(prompt):
    """
    Forwards to either raw_input or input, depending on Python version
    """
    try:
        return raw_input(prompt)
    except NameError:
        return input(prompt)


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
        prefix = urlunparse(
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
    service_url = urlunparse(
            (get_protocol(request), request.get_host(),
            request.path, '', '', ''),
    )
    query_params = request.GET.copy()
    query_params[REDIRECT_FIELD_NAME] = redirect_url or \
            get_redirect_url(request)
    # The CAS server may have added the ticket as an extra query
    # parameter upon checking the credentials - ensure it is ignored
    query_params.pop('ticket', None)
    service_url += '?' + urlencode(query_params)
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
