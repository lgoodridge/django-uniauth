# django-uniauth

[![travis][travis-image]][travis-url]
[![pyver][pyver-image]][pyver-url]
[![djangover][djangover-image]][djangover-url]
[![pypi][pypi-image]][pypi-url]

`django-uniauth` is an app for allowing authentication through services commonly used by universities, such as [CAS](https://www.apereo.org/projects/cas), while also permitting custom authentication schemes. This approach allows developers to leverage the user data contained within university databases, without strictly tethering themselves to those services.

The app was designed to replace key features of the built-in `django.contrib.auth` package. Developers may simply replace the appropriate backends and URLs and let UniAuth handle authentication entirely if they wish. However, the app is also fully customizable, and components may be swapped with compatible replacements if desired.

## Features

 - Supports Python 2.7, 3.5+
 - Supports Django 1.11, 2.x
 - Supports using a [custom User model](https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#specifying-a-custom-user-model)
 - Supports using email addresses as the ["username" field](https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#django.contrib.auth.models.CustomUser.USERNAME_FIELD)
 - Users can link multiple email addresses and use any for authentication
 - Supports CAS authentication and Single Sign On

## Installation

Install using [pip](http://www.pip-installer.org/):

    pip install django-uniauth

Add 'uniauth' to your `INSTALLED_APPS` setting:

    INSTALLED_APPS = [
        ...
        uniauth,
    ]

Add the desired Uniauth authentication backends. For example:

    AUTHENTICATION_BACKENDS = [
        'uniauth.backends.LinkedEmailBackend',
        'uniauth.backends.CASBackend',
    ]

Lastly, include the `uniauth` URLS in your `urls.py`:

    URL_PATTERNS = [
        ...
        path('accounts/', include('uniauth.urls', namespace='uniauth')),
    ]

## Email Setup

Uniauth will send emails to users when necessary, such as to verify email addresses or for resetting passwords. During development, it may be sufficient to log these emails to the console - this is accomplished by adding the following to `settings.py`:

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

On production, a real email backend should be properly set up. See the docs on [setting up an SMTP backend](https://docs.djangoproject.com/en/2.1/topics/email/#smtp-backend) for more information.

## Settings

Uniauth uses the following settings from the `django.contrib.auth` package:

 - [`LOGIN_URL`]( https://docs.djangoproject.com/en/2.1/ref/settings/#login-url): Determines where to redirect the user for login, particularly when using the `@login_required` decorator. Defaults to `/accounts/login/`.
 - [`PASSWORD_RESET_TIMEOUT_DAYS`](https://docs.djangoproject.com/en/2.1/ref/settings/#password-reset-timeout-days): Determines how long password reset and email verification links are valid after being generated. Defaults to `3`.

The following custom settings are also used:

 - `UNIAUTH_ALLOW_SHARED_EMAILS`: Whether to allow a single email address to be linked to multiple profiles. Primary email addresses (the value set in the user's `email` field) must be unique regardless. Defaults to `True`.
 - `UNIAUTH_ALLOW_STANDALONE_ACCOUNTS`: Whether to allow users to log in via an Institution Account (such as via CAS) without linking it to a Uniauth profile first. If set to `False`, users will be required to create or link a profile to their Institution Accounts before being able to access views protected by the `@login_required` decorator. Defaults to `True`.
 - `UNIAUTH_FROM_EMAIL`: Determines the "from" email address when UniAuth sends an email, such as for email verification or password resets. Defaults to `uniauth@example.com`.
 - `UNIAUTH_LOGIN_DISPLAY_STANDARD`: Whether the email address / password form is shown on the `login` view. If `False`, the form, "Create an Account" link, and "Forgot Password" link are hidden, and POST requests for the view will be ignored. Defaults to `True`.
 - `UNIAUTH_LOGIN_DISPLAY_CAS`: Whether the option to sign in via CAS is shown on the `login` view. If `True`, there must be at least one `Institution` in the database to log into. Also, at least one of `UNIAUTH_LOGIN_DISPLAY_STANDARD` or `UNIAUTH_LOGIN_DISPLAY_CAS` must be `True`. Violating either of these constraints will result in an `ImproperlyConfigured` Exception. Defaults to `True`.
 - `UNIAUTH_LOGIN_REDIRECT_URL`: Where to redirect the user after logging in, if no next URL is provided. Defaults to `/`.
 - `UNIAUTH_LOGOUT_REDIRECT_URL`: Where to redirect the user after logging out, if no next URL is provided. If this setting is `None`, and a next URL is not provided, the logout template is rendered instead. Defaults to `None`.
 - `UNIAUTH_LOGOUT_CAS_COMPLETELY`: Whether to log the user out of CAS on logout if the user originally logged in via CAS. Defaults to `False`.
 - `UNIAUTH_MAX_LINKED_EMAILS`: The maximum number of emails a user can link to their profile. If this value is less than or equal to 0, there is no limit to the number of linked emails. Defaults to 20.
 - `UNIAUTH_PERFORM_RECURSIVE_MERGING`: Whether to attempt to recursively merge One-to-One fields when merging users due to linking two existing accounts together. If `False`, One-to-One fields for the user being linked in will be deleted if the primary user has a non-null value for that field.

## Users in UniAuth

UniAuth supports any custom User model, so long as the model has `username` and `email` fields. The `email` serves as the primary identifying field within UniAuth, with the `username` being set to an arbitrary unique value to support packages that require it. Once a user's profile has been activated, other apps are free to change the `username` without disrupting UniAuth's behavior.

Users are created by either completing the Sign Up form, or logging in via an `InstitutionAccount`. In the former case, they are given a username beginning with `tmp-`, followed by a unique suffix, and an empty `email` field. When the first email for a user has been verified, their profile is considered fully activated, the `email` field is set to the verified email, and the `username` field is arbitrarily set to that email address as well, unless it is taken. In the latter case, they are given a username describing how they were authenticated, along with the institution they signed into and their ID for that institution. They will keep this username and have an empty `email` field until they link their account to a verified Uniauth profile.

Users may have multiple email addresses linked to their profile, any of which may be used for authentication (if one of the `LinkedEmail` [UniAuth backends](https://github.com/lgoodridge/UniAuth#backends) are used), or for password reset. The address set in the user's `email` field is considered the "primary email", and is the only one that must be unique across all users. Users may change which linked email is their primary email address at any point via the `settings` page, so long as that primary email is not taken by another user.

Users may also have multiple `InstitutionAccounts` linked to their profile. These represent alternative ways of logging in, other than the standard username/email + password form. For example, if a University offers authentication via CAS, a user may link their CAS username for that university to their UniAuth profile, so that logging with CAS authenticates them as the proper user. All `InstitutionAccounts` must be linked to a profile in order to be used for authentication.

## Backends

To use UniAuth as intended, either the `LinkedEmailBackend` or the `UsernameOrLinkedEmailBackend` should be included in your `AUTHENTICATION_BACKENDS` setting, along with the backends for any other authentication methods you wish to support.

### CASBackend:

The `CASBackend` is inspired from the [`django-cas-ng backend`](https://github.com/mingchen/django-cas-ng/blob/master/django_cas_ng/backends.py) of the same name, and is largely a simplified version of that class. This backend's `authenticate` method accepts an `institution`, a `ticket`, and a `service` URL to redirect to on successful authentication, and attempts to verify that ticket with the institution's CAS server.

If verification succeeds, it looks for an `InstitutionAccount` matching that CAS username, and returns the user for the associated profile. If it succeeds, but there is no such `InstitutionAccount`, a temporary user is created, and the client will eventually be prompted to link this username to an existing UniAuth profile, or create one. If verification fails, authentication fails as well.

### LinkedEmailBackend:

This backend's `authenticate` method accepts an email and password as keyword arguments, and checks the password against all users with that email linked to their account. If an `email` is not explicitly provided, a few other common field names (such as `email_address` and `username`) are checked and used if found.

**Note:** Since the default Django admin page uses same Authentication Backends as the rest of the site, replacing the default `ModelBackend` with this one will result in usernames no longer being recognized on the admin login screen. You will need to log in with a superuser's email address and password, or use the below `UsernameOrLinkedEmailBackend` instead.

### UsernameOrLinkedEmailBackend:

Identical to the above class, except the provided `email` argument is also checked against each user's `username`.

## Commands

UniAuth provides the following managment commands:

 - `add_institution <name> <cas_server_url>` Adds an `Institution` with the provided name and CAS server URL to the database.
 - `remove_institution <slug>` Removes the `Institution` with the provided slug from the database. This action removes any `InstitutionAccounts` for that instiutiton in the process.

## Views

The five views you will likely care about the most are `login`, `logout`, `signup`, `password-reset`, and `settings`:

 - `/login/`: Displays a page allowing users to log in by entering a username/email and password, or via a supported backend, such as CAS. Also displays links for creating an account directly, and for resetting passwords.
 - `/logout/`: Logs out the user. The behavior and redirect location of the log out is determined by the app's settings.
 - `/signup/`: Prompts user for a primary email address, and a password, then sends a verification email to that address to activate the account.
 - `/password-reset/`: Prompts user for an email address, then sends an email to that address containing a link for resetting the password. If no users have the entered email address linked to their account, no email is sent. If multiple users have that address linked, an email is sent for each potential user.
 - `/settings/`: Allows users to perform account related actions, such as link more email addresses, choose the primary email address, link more Institution Accounts, or change their password.

The remaining views are used internally by UniAuth, and should not be linked to from outside the app:

 - `/cas-login/`: If a user chooses to log in via CAS, this view is called with the institution the user wishes to log into as an argument. The view will first redirect to the institution's CAS server and attempt to get a ticket, then return to the original page and attempt to authenticate with that ticket, via the `CASBackend`.
 - `/link-to-account/`: If the user is logged into an `InstitutionAccount` not yet linked to a UniAuth profile, this view offers them the choice between linking it to an existing profile, or creating a new one, and linking it to that upon activation.
 - `/link-from-account/`: If the user is logged into an activated UniAuth profile, this view gives them the opportunity to log into an institution via a supported backend, then link that `InstitutionAccount` to the current profile.
 - `/verify-token/`: Intermediate page used during the email verification process. Verifies the token contained within the link sent to the email address.
 - `/password-reset-*/`: Intermediate pages used during the password reset process. Are nearly identical to the [built-in password reset views](https://docs.djangoproject.com/en/2.1/topics/auth/default/#django.contrib.auth.views.PasswordResetView) provided by the `django.contrib.auth` package.

UniAuth also implements its own version of the `@login_required` decorator, which ensure the user is logged in with an activated UniAuth profile before accessing the view. It may be used identically to the [built-in `@login_required` decorator](https://docs.djangoproject.com/en/2.1/topics/auth/default/#the-login-required-decorator), and should be added to your own views in place of the default version.

## Template Customization

The presentation of the views can be easily changed by overriding the appropriate template(s). For example, to add your own stylesheet to the UniAuth templates, create a `uniauth` folder in your `templates` directory, and add a `base-site.html` file to override the default one like so:

    {% extends "uniauth/base.html" %}

    {% load static from staticfiles %}

    {% block shared-head %}
    <link rel="shortcut icon" href="{% static 'uniauth/img/favicon.ico' %}"/>
    <link href="{% static 'path/to/custom-style.css' %}" rel="stylesheet" type="text/css"/>
    {% endblock %}

    {% block body %}
    <div id="wrapper">
        <div id="page-wrapper" class="lavender-bg">
            <div id="content-wrapper">
                <div id="top-background"></div>
                {% block content %}
                {% endblock %}
            </div>
        </div>
    </div>
    {% endblock %}

More specific changes can be made by overriding the appropriate template.

## URL Parameters

All views except `/settings/` persist URL parameters to their final destination. This means you can add a query string to the `login` URL, and have it apply to the `UNIAUTH_LOGIN_REDIRECT_URL` page, for example.

The only URL parameter that is not preserved is the `next` variable, which indicates the desired location to redirect to after business in the current view is completed. This variable is consumed upon successful redirection to that location, and can be used to dynamically control how the app behaves after visiting a view.

## Usage Notes

This app should not be added to a project that already has registered users, because those users will not have the required UniAuth profile attached them, and therefore will not be valid.

This app provides only the Princeton institution by default as an example. Additional institutions should be configured post-installation as necessary, using the `add_institution` and `remove_institution` commands.

The source repository contains a `demo_app` directory which demonstrates how to setup a simple Django app to use UniAuth. This app has no functionality, and exists solely to show off the installable `uniauth` app. A quick-start guide for integrating UniAuth can be found [here](https://github.com/lgoodridge/UniAuth/tree/master/demo_app).

[djangover-image]: https://img.shields.io/pypi/djversions/django-uniauth.svg?label=django
[djangover-url]: https://pypi.python.org/pypi/django-uniauth/

[license-image]: https://img.shields.io/github/license/lgoodridge/Uniauth.svg
[license-url]: https://github.com/lgoodridge/UniAuth/blob/master/LICENSE.md

[pypi-image]: https://img.shields.io/pypi/v/django-uniauth.svg
[pypi-url]: https://pypi.python.org/pypi/django-uniauth/

[pyver-image]: https://img.shields.io/pypi/pyversions/django-uniauth.svg
[pyver-url]: https://pypi.python.org/pypi/django-uniauth/

[status-image]: https://img.shields.io/pypi/status/django-uniauth.svg
[status-url]: https://pypi.python.org/pypi/django-uniauth/

[travis-image]: https://img.shields.io/travis/lgoodridge/UniAuth.svg?style=flat
[travis-url]: https://travis-ci.com/lgoodridge/UniAuth
