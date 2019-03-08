from cas import CASClient
from django.contrib.auth import authenticate, login as auth_login, \
        logout as auth_logout, REDIRECT_FIELD_NAME
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.views import PasswordResetCompleteView, \
        PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404, HttpResponseBadRequest, \
        HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.urls.exceptions import NoReverseMatch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from uniauth.decorators import login_required
from uniauth.forms import AddLinkedEmailForm, ChangePrimaryEmailForm, \
        LinkedEmailActionForm, LoginForm, PasswordChangeForm, \
        PasswordResetForm, SetPasswordForm, SignupForm
from uniauth.merge import merge_model_instances
from uniauth.models import Institution, InstitutionAccount, LinkedEmail
from uniauth.tokens import token_generator
from uniauth.utils import choose_username, decode_pk, encode_pk, \
        get_account_username_split, get_protocol, get_random_username, \
        get_redirect_url, get_service_url, get_setting, is_tmp_user, \
        is_unlinked_account
try:
    from urllib import urlencode
    from urlparse import urlunparse
except ImportError:
    from urllib.parse import urlencode, urlunparse


def _get_global_context(request):
    """
    Returns a dictionary of context data shared by the views
    """
    context = {}

    # Returns the reverse lookup URL of the provided view with
    # the provided slug argument. Returns None if the view is
    # not accessible under the current configuration
    def get_reversed_url_or_none(view_name, slug):
        try:
            return reverse('uniauth:%s' % view_name, args=[slug])
        except NoReverseMatch:
            return None

    # Add a list of Institution tuples, with each containing:
    # (name, slug, CAS login url, Profile link URL)
    institutions = Institution.objects.all()
    institutions = list(map(lambda x: (x.name, x.slug,
            get_reversed_url_or_none("cas-login", x.slug),
            get_reversed_url_or_none("link-from-profile", x.slug)),
            institutions))
    context['institutions'] = institutions

    # Add the query parameters, as a string
    query_params = urlencode(request.GET)
    prefix = '?' if query_params else ''
    context['query_params'] = prefix + query_params

    return context


def _login_success(request, user, next_url, drop_params=[]):
    """
    Determines where to go upon successful authentication:
    Redirects to link tmp account page if user is a temporary
    user, redirects to next_url otherwise.

    Any query parameters whose key exists in drop_params are
    not propogated to the destination URL
    """
    query_params = request.GET.copy()

    # Drop all blacklisted query parameters
    for key in drop_params:
        if key in query_params:
            del query_params[key]

    # Temporary users should redirect to the link-to-profile page
    if is_tmp_user(user):
        query_params[REDIRECT_FIELD_NAME] = next_url
        return HttpResponseRedirect(reverse('uniauth:link-to-profile') + \
                '?' + urlencode(query_params))

    # All other users should redirect to next_url
    else:
        suffix = ''
        if REDIRECT_FIELD_NAME in query_params:
            del query_params[REDIRECT_FIELD_NAME]
        if len(query_params) > 0:
            suffix = '?' + urlencode(query_params)
        return HttpResponseRedirect(next_url + suffix)


def login(request):
    """
    Authenticates the user, then redirects them to the
    next page, defaulting to the URL specified by the
    UNIAUTH_LOGIN_REDIRECT_URL setting.

    Offers users the choice between logging in with their
    Uniauth credentials, or through the CAS interface for
    any supported institution.
    """
    next_url = request.GET.get('next')
    context = _get_global_context(request)

    if not next_url:
        next_url = get_redirect_url(request)

    # If the user is already authenticated, proceed to next page
    if request.user.is_authenticated:
        return _login_success(request, request.user, next_url)

    display_standard = get_setting('UNIAUTH_LOGIN_DISPLAY_STANDARD')
    display_cas = get_setting('UNIAUTH_LOGIN_DISPLAY_CAS')
    num_institutions = len(context['institutions'])

    # Ensure the login settings are configured correctly
    if not display_standard and not display_cas:
        err_msg = "At least one of '%s' and '%s' must be True." % \
                ('UNIAUTH_LOGIN_DISPLAY_STANDARD', 'UNIAUTH_LOGIN_DISPLAY_CAS')
        raise ImproperlyConfigured(err_msg)
    if display_cas and num_institutions == 0:
        err_msg = ("'%s' is True, but there are no Institutions in the "
                "database to log into!") % 'UNIAUTH_LOGIN_DISPLAY_CAS'
        raise ImproperlyConfigured(err_msg)

    context['display_standard'] = display_standard
    context['display_cas'] = display_cas
    context['num_institutions'] = num_institutions

    # If we aren't displaying the standard login form,
    # we're just displaying the CAS login options
    if not display_standard:
        institutions = context['institutions']
        query_params = context['query_params']

        # If there's only one possible institution to log
        # into, redirect to its CAS login page immediately
        if num_institutions == 1:
            return HttpResponseRedirect(institutions[0][2] + query_params)

        # Otherwise, render the page (without the Login form)
        else:
            return render(request, 'uniauth/login.html', context)

    # If we are displaying the login form, and it's
    # a POST request, attempt to validate the form
    elif request.method == "POST":
        form = LoginForm(request, request.POST)

        # Authentication successful: setup session + proceed
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            request.session['auth-method'] = "uniauth"
            return _login_success(request, user, next_url)

        # Authentication failed: render form errors
        else:
            context['form'] = form
            return render(request, 'uniauth/login.html', context)

    # Otherwise, render a blank Login form
    else:
        form = LoginForm(request)
        context['form'] = form
        return render(request, 'uniauth/login.html', context)


def cas_login(request, institution):
    """
    Redirects to the CAS login URL, or verifies the
    CAS ticket, if provided.

    Accepts the slug of the institution to log in to.
    """
    next_url = request.GET.get('next')
    ticket = request.GET.get('ticket')

    # Ensure there is an institution with the provided slug
    try:
        institution = Institution.objects.get(slug=institution)
    except Institution.DoesNotExist:
        raise Http404

    if not next_url:
        next_url = get_redirect_url(request, use_referer=True)

    # If the user is already authenticated, proceed to next page
    if request.user.is_authenticated:
        return _login_success(request, request.user, next_url)

    service_url = get_service_url(request, next_url)
    client = CASClient(version=2, service_url=service_url,
            server_url=institution.cas_server_url)

    # If a ticket was provided, attempt to authenticate with it
    if ticket:
        user = authenticate(request=request, institution=institution,
                ticket=ticket, service=service_url)

        # Authentication successful: setup session + proceed
        if user:
            if not request.session.exists(request.session.session_key):
                request.session.create()
            auth_login(request, user)
            request.session['auth-method'] = "cas-" + institution.slug
            return _login_success(request, user, next_url, ["ticket"])

        # Authentication failed: raise permission denied
        else:
            raise PermissionDenied("Verification of CAS ticket failed.")

    # If no ticket was provided, redirect to the
    # login URL for the institution's CAS server
    else:
        return HttpResponseRedirect(client.get_login_url())


def logout(request):
    """
    Logs the user out of their Uniauth account, and
    redirects to the next page, defaulting to the URL
    specified by the UNIAUTH_LOGOUT_REDIRECT_URL setting.

    If no redirect page is set (URL parameter not given
    and UNIAUTH_LOGOUT_REDIRECT_URL is None), renders the
    logout template.

    Also logs the user out of CAS if they logged in
    via CAS, and the UNIAUTH_LOGOUT_CAS_COMPLETELY
    setting is true.
    """
    next_page = request.GET.get('next')
    auth_method = request.session.get('auth-method')

    if not next_page and get_setting('UNIAUTH_LOGOUT_REDIRECT_URL'):
        next_page = get_redirect_url(request,
                get_setting('UNIAUTH_LOGOUT_REDIRECT_URL'))

    # Formally log out user
    auth_logout(request)

    # Determine whether the user logged in through an institution's CAS
    institution = None
    if auth_method and auth_method.startswith("cas-"):
        try:
            institution = Institution.objects.get(slug=auth_method[4:])
        except Institution.DoesNotExist:
            pass

    # If we need to logout an institution's CAS,
    # redirect to that CAS server's logout URL
    if institution and get_setting('UNIAUTH_LOGOUT_CAS_COMPLETELY'):
        redirect_url = urlunparse(
                (get_protocol(request), request.get_host(),
                    next_page or reverse('uniauth:logout'), '', '', '')
        )
        client = CASClient(version=2, service_url=get_service_url(request),
                server_url=institution.cas_server_url)
        return HttpResponseRedirect(client.get_logout_url(redirect_url))

    # If next page is set, proceed to it
    elif next_page:
        return HttpResponseRedirect(next_page)

    # Otherwise, render the logout view
    else:
        return render(request, 'uniauth/logout.html')


def _send_verification_email(request, to_email, verify_email):
    """
    Sends an email (to to_email) containing a link to
    verify the target email (verify_email) as a linked
    email address for the user.

    Expects to_email as a string, and verify_email as
    a LinkedEmail model instance.
    """
    subject = "Verify your email address."
    message = render_to_string('uniauth/verification-email.html', {
        'protocol': get_protocol(request),
        'domain': get_current_site(request),
        'pk': encode_pk(verify_email.pk),
        'token': token_generator.make_token(verify_email),
        'query_params': _get_global_context(request)["query_params"],
    })
    email = EmailMessage(subject, message, to=[to_email],
            from_email=get_setting('UNIAUTH_FROM_EMAIL'))
    email.send()


def signup(request):
    """
    Creates a new Uniauth profile with the provided
    primary email address and password.

    Prompts user to verify the email address before
    profile is fully created.
    """
    next_url = request.GET.get('next')
    context = _get_global_context(request)

    if not next_url:
        next_url = get_redirect_url(request)

    # If the user is already authenticated + has a Uniauth
    # profile, proceed to next page
    if request.user.is_authenticated and not is_tmp_user(request.user) \
            and not is_unlinked_account(request.user):
        return HttpResponseRedirect(next_url)

    # If it's a POST request, attempt to validate the form
    if request.method == "POST":
        form = SignupForm(request.POST)

        # Validation successful: setup temporary user
        if form.is_valid():
            form_email = form.cleaned_data['email']
            user = request.user

            # If the user is not already authenticated, create a User
            if not user or not user.is_authenticated:
                tmp_username = get_random_username()
                user_model = get_user_model()
                user = user_model.objects.create(username=tmp_username)

            # Set user's password + create linked email
            user.set_password(form.cleaned_data["password1"])
            user.save()
            email, _ = LinkedEmail.objects.get_or_create(profile=user.profile,
                    address=form_email, is_verified=False)

            # Send verification email + render waiting template
            _send_verification_email(request, email.address, email)
            return render(request, 'uniauth/verification-waiting.html',
                    {'email': email.address, 'is_signup': True})

        # Validation failed: render form errors
        else:
            context['form'] = form
            return render(request, 'uniauth/signup.html', context)

    # Otherwise, render a blank Signup form
    else:
        form = SignupForm()
        context['form'] = form
        return render(request, 'uniauth/signup.html', context)


@login_required
def settings(request):
    """
    Allows the user to link additional emails, change
    the primary email address of, and link additional
    institution accounts to their Uniauth profile.
    """
    context = _get_global_context(request)
    context['email_resent'] = None
    context['email_added'] = None
    context['password_changed'] = False

    action_email_form = None
    add_email_form = None
    change_email_form = None
    change_password_form = None

    # This page may only be accessed by users with Uniauth profiles:
    # if the user is logged in with an unlinked InsitutionAccount,
    # redirect them to the link page
    if is_unlinked_account(request.user):
        params = urlencode({'next': reverse('uniauth:settings')})
        return HttpResponseRedirect(reverse('uniauth:link-to-profile') + \
                '?' + params)

    # If it's a POST request, determine which form was submitted
    if request.method == 'POST':

        # Linked Email Action Form submitted: validate the
        # delete / resend action + perform it if able
        if request.POST.get('action-email-submitted'):
            action_email_form = LinkedEmailActionForm(request.POST)
            if action_email_form.is_valid():
                delete_pk = action_email_form.cleaned_data.get("delete_pk")
                resend_pk = action_email_form.cleaned_data.get("resend_pk")

                # If they asked to delete a linked email: it must
                # belong to the user and not be the primary address
                if delete_pk:
                    try:
                        email = LinkedEmail.objects.get(pk=delete_pk)
                        if email.profile.user == request.user and \
                                email.address != request.user.email:
                            email.delete()
                    except LinkedEmail.DoesNotExist:
                        pass

                # If they asked to resend a verification email: it
                # must belong to the user and be pending verification
                elif resend_pk:
                    try:
                        email = LinkedEmail.objects.get(pk=resend_pk)
                        if email.profile.user == request.user and \
                                not email.is_verified:
                            _send_verification_email(request,
                                    email.address, email)
                            context['email_resent'] = email.address
                    except LinkedEmail.DoesNotExist:
                        pass

                action_email_form = None

        # Add Linked Email Form submitted: validate and create
        # new linked email + send verification email
        elif request.POST.get('add-email-submitted'):
            add_email_form = AddLinkedEmailForm(request.user, request.POST)
            if add_email_form.is_valid():
                email = LinkedEmail.objects.create(profile=request.user.profile,
                        address=add_email_form.cleaned_data["email"],
                        is_verified=False)
                _send_verification_email(request, email.address, email)
                context['email_added'] = email.address
                add_email_form = None

        # Change Primary Email Address Form submitted:
        # validate and set user's primary email address
        elif request.POST.get('change-email-submitted'):
            change_email_form = ChangePrimaryEmailForm(request.user,
                    request.POST)
            if change_email_form.is_valid():
                request.user.email = change_email_form.cleaned_data["email"]
                request.user.save()
                change_email_form = None

        # Change Password Form submitted: validate and set password
        elif request.POST.get('change-password-submitted'):
            change_password_form = PasswordChangeForm(request.user,
                    request.POST)
            if change_password_form.is_valid():
                change_password_form.save()
                update_session_auth_hash(request, request.user)
                context['password_changed'] = True
                change_password_form = None

    # Create blank versions of all non-bound forms
    if action_email_form is None:
        action_email_form = LinkedEmailActionForm(request.user)
    if add_email_form is None:
        add_email_form = AddLinkedEmailForm(request.user)
    if change_email_form is None:
        change_email_form = ChangePrimaryEmailForm(request.user)
    if change_password_form is None:
        change_password_form = PasswordChangeForm(request.user)

    # Assemble the context and render
    context['action_email_form'] = action_email_form
    context['add_email_form'] = add_email_form
    context['change_email_form'] = change_email_form
    context['change_password_form'] = change_password_form
    return render(request, 'uniauth/settings.html', context)


def _add_institution_account(profile, slug, cas_id):
    """
    Accepts an institution slug and cas ID and links an
    InsitutionAccount to the provided Uniauth user.
    """
    institution = Institution.objects.get(slug=slug)
    InstitutionAccount.objects.create(profile=profile,
            institution=institution, cas_id=cas_id)


def link_to_profile(request):
    """
    If the user is a temporary one who was logged in via
    an institution (not through a Uniauth profile), offers
    them the choice between logging to an existing Uniauth
    account or creating a new one.

    The institution account is (eventually) linked to the
    Uniauth profile the user logged into / created.
    """
    next_url = request.GET.get('next')
    context = _get_global_context(request)

    if not next_url:
        next_url = get_redirect_url(request)

    params = urlencode({'next': next_url})
    context['next_url'] = next_url

    # If the user is not authenticated at all, redirect to login page
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('uniauth:login') + '?' + params)

    # If the user is already authenticated + verified, proceed to next page
    if not is_tmp_user(request.user) and not is_unlinked_account(request.user):
        return HttpResponseRedirect(next_url)

    # If the user is temporary, but was not logged in via an institution
    # (e.g. created through Uniauth, but not verified), redirect to signup
    if not is_unlinked_account(request.user):
        return HttpResponseRedirect(reverse('uniauth:signup') + '?' + params)

    # At this point, we've ensured the user is temporary and was
    # logged in via an institution. We just need to handle the
    # Login Form, if the user chooses to link to an existing account.

    # If it's a POST request, attempt to validate the form
    if request.method == "POST":
        form = LoginForm(request, request.POST)

        # Authentication successful
        if form.is_valid():
            unlinked_user = request.user
            username_split = get_account_username_split(request.user.username)

            # Log in as the authenticated Uniauth user
            user = form.get_user()
            auth_login(request, user)

            # Merge the unlinked account into the logged in profile,
            # then add the institution account described by the username
            merge_model_instances(user, [unlinked_user])
            _add_institution_account(user.profile, username_split[1],
                    username_split[2])

            slug = username_split[1]
            context['institution'] = Institution.objects.get(slug=slug)
            return render(request, 'uniauth/link-success.html', context)

        # Authentication failed: render form errors
        else:
            context['form'] = form
            return render(request, 'uniauth/link-to-profile.html', context)

    # Otherwise, render a blank Login form
    else:
        form = LoginForm(request)
        context['form'] = form
        return render(request, 'uniauth/link-to-profile.html', context)


def link_from_profile(request, institution):
    """
    Attempts to authenticate a CAS account for the provided
    institution, and links it to the current Uniauth profile
    if successful.
    """
    next_url = request.GET.get('next')
    ticket = request.GET.get('ticket')

    # Ensure there is an institution with the provided slug
    try:
        institution = Institution.objects.get(slug=institution)
    except Institution.DoesNotExist:
        raise Http404

    if not next_url:
        next_url = get_redirect_url(request, use_referer=True)

    # If the user is not already logged into a verified
    # Uniauth account, raise permission denied
    if not request.user.is_authenticated or is_tmp_user(request.user) \
            or is_unlinked_account(request.user):
        raise PermissionDenied("Must be logged in as verified Uniauth user.")

    service_url = get_service_url(request, next_url)
    client = CASClient(version=2, service_url=service_url,
            server_url=institution.cas_server_url)

    # If a ticket was provided, attempt to authenticate with it
    if ticket:
        user = authenticate(request=request, institution=institution,
                ticket=ticket, service=service_url)

        # Authentication successful: link to Uniauth profile if
        # the institution account has not been linked yet + proceed
        if user:
            if is_unlinked_account(user):
                merge_model_instances(request.user, [user])
                username_split = get_account_username_split(user.username)
                _add_institution_account(request.user.profile,
                        username_split[1], username_split[2])

            return HttpResponseRedirect(next_url)

        # Authentication failed: raise permission denied
        else:
            raise PermissionDenied("Verification of CAS ticket failed")

    # If no ticket was provided, redirect to the
    # login URL for the institution's CAS server
    else:
        return HttpResponseRedirect(client.get_login_url())


def verify_token(request, pk_base64, token):
    """
    Verifies a token generated for validating an email
    address, and notifies the user whether verification
    was successful.
    """
    next_url = request.GET.get('next') or request.GET.get(REDIRECT_FIELD_NAME)
    context = {'next_url': next_url, 'is_signup': False}
    user_model = get_user_model()

    # Attempt to get the linked email to verify
    try:
        email_pk = decode_pk(pk_base64)
        email = LinkedEmail.objects.get(pk=email_pk)
    except (TypeError, ValueError, OverflowError, user_model.DoesNotExist,
            LinkedEmail.DoesNotExist):
        email = None

    # In the unlikely scenario that a user is trying to sign up
    # with an email another verified user has as a primary email
    # address, reject verification immediately
    if email is not None and is_tmp_user(email.profile.user) and \
            get_user_model().objects.filter(email=email.address).exists():
        email = None

    # If the token successfully verifies, update the linked email
    if email is not None and token_generator.check_token(email, token):
        email.is_verified = True
        email.save()

        # If the user this email is linked to is a temporary
        # one, change it to a fully registered user
        user = email.profile.user
        if is_tmp_user(user) or is_unlinked_account(user):
            context['is_signup'] = True
            old_username = user.username

            # Change the email + username to the verified email
            user.email = email.address
            user.username = choose_username(user.email)
            user.save()

            # If the user was created via CAS, add the institution
            # account described by the temporary username
            if old_username.startswith("cas"):
                username_split = get_account_username_split(old_username)
                _add_institution_account(user.profile, username_split[1],
                        username_split[2])

        # If UNIAUTH_ALLOW_SHARED_EMAILS is False, and there were
        # pending LinkedEmails for this address on other accounts,
        # delete them
        if not get_setting('UNIAUTH_ALLOW_SHARED_EMAILS'):
            LinkedEmail.objects.filter(address=email.address,
                    is_verified=False).delete()

        return render(request, 'uniauth/verification-success.html', context)

    # If anything went wrong, just render the failed verification template
    else:
        return render(request, 'uniauth/verification-failure.html', context)


# The password reset views are pulled from the django.conrib.auth
# package, and are used largely unmodified. We just set things like
# the template and reverse URL names to use Uniauth's files + naming
# scheme.

class PasswordReset(PasswordResetView):
    """
    Asks user for an email address to send the link to, then
    sends a password reset link to that address.

    If no user has that email address linked to their account,
    no email is sent, unbeknownst to the user.
    """
    email_template_name = 'uniauth/password-reset-email.html'
    form_class = PasswordResetForm
    from_email = get_setting('UNIAUTH_FROM_EMAIL')
    success_url = reverse_lazy('uniauth:password-reset-done')
    template_name = 'uniauth/password-reset.html'

    def form_valid(self, form):
        """
        Add global context data before composing reset email
        """
        self.extra_email_context = _get_global_context(self.request)
        return super(PasswordReset, self).form_valid(form)


class PasswordResetDone(PasswordResetDoneView):
    """
    Shows success message once email was sent.
    """
    template_name = 'uniauth/password-reset-done.html'


class PasswordResetVerify(PasswordResetConfirmView):
    """
    Verifies the provided token, and prompts user for their
    new password if successful.
    """
    form_class = SetPasswordForm
    success_url = reverse_lazy('uniauth:password-reset-verify-done')
    template_name = 'uniauth/password-reset-verify.html'

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        """
        Save query params in session if available.
        """
        query_params = _get_global_context(self.request)['query_params']
        if query_params:
            self.request.session['password-reset-query-params'] = query_params
        return super(PasswordResetVerify, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        """
        Set success_url to include query params saved in session
        """
        query_params = self.request.session\
                .pop('password-reset-query-params', '')
        self.success_url += query_params
        return super(PasswordResetVerify, self).form_valid(form)


class PasswordResetVerifyDone(PasswordResetCompleteView):
    """
    Shows success message once new password is set.
    """
    template_name = 'uniauth/password-reset-verify-done.html'

    def get_context_data(self, **kwargs):
        """
        Add global context data to template context.
        """
        context = super(PasswordResetVerifyDone, self)\
                .get_context_data(**kwargs)
        context.update(_get_global_context(self.request))
        return context

