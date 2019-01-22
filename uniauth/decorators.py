from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from uniauth.utils import is_tmp_user


def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME,
        login_url=None):
    """
    Replacement for django's built-in login_required
    decorator that also requires user to not be a
    temporary user (must have completed signup process).

    It can be used identically to the built-in version.
    """
    actual_decorator = user_passes_test(
            lambda u: u.is_authenticated and not is_tmp_user(u),
            login_url=login_url,
            redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

