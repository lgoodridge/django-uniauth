from cas import CASClient
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from uniauth.models import InstitutionAccount, UserProfile
from uniauth.utils import is_tmp_user


class CASBackend(ModelBackend):
    """
    Authentication backend that verifies A CAS ticket
    with the server for the provided institution and
    returns either the authenticated Uniauth user (if
    one already exists), or a newly created user with
    a temporary username otherwise.
    """

    def authenticate(self, request, institution, ticket, service):
        user_model = get_user_model()

        # Attempt to verify the ticket with the institution's CAS server
        client = CASClient(version=2, service_url=service,
                server_url=institution.cas_server_url)
        username, attributes, pgtiou = client.verify_ticket(ticket)

        # Add the attributes returned by the CAS server to the session
        if request and attributes:
            request.session['attributes'] = attributes

        # If no username was returned, verification failed
        if not username:
            return None

        # Attempt to find a user possessing an account
        # with that username for the institution
        try:
            user = InstitutionAccount.objects.get(cas_id=username,
                    institution=institution).profile.user
        except InstitutionAccount.DoesNotExist:
            user = None

        # If such a user does not exist, get or create
        # one with a deterministic, CAS username
        if not user:
            temp_username = "cas-%s-%s" % (institution.slug, username)
            user, created = user_model._default_manager.get_or_create(
                    **{user_model.USERNAME_FIELD: temp_username})

        return user


class LinkedEmailBackend(ModelBackend):
    """
    Authentication backend allowing users to authenticate
    with any email address linked to the account, along
    with their password.

    Note: 'username' is still supported as an argument for
    authenticate to facilitate easier swapping of this
    backend with the UsernameOrLinkedEmailBackend, and
    other authentication schemes using a username argument.
    """

    def _get_users(self, user_model, email):
        """
        Query for users with a verified linked email
        address matching the provided email value
        """
        return user_model._default_manager.filter(
                uniauth_profile__linked_emails__address__iexact=email,
                uniauth_profile__linked_emails__is_verified=True
        ).all()

    def authenticate(self, request, email=None, password=None, **kwargs):
        user_model = get_user_model()

        # If email field was not provided, check for
        # alternative names, or for a "username" field
        if email is None:
            email = kwargs.get('email_address')
            if email is None:
                email = kwargs.get('username')

                # If a custom user model is being used, check for
                # the email in the specified username field
                if email is None:
                    email = kwargs.get(user_model.USERNAME_FIELD)

        # Get the user(s) who own the provided email address
        users = self._get_users(user_model, email)

        # If there were no matching users, run the password
        # hasher once, to guard against timing attacks
        if not users:
            user_model().set_password(password)
            return None

        # Otherwise, check the password for each matched user
        for user in users:
            if user.check_password(password):
                return user
        return None


class UsernameOrLinkedEmailBackend(LinkedEmailBackend):
    """
    Authenticaton backend allowing users to authenticate
    with their username, or any email address linked to
    the account, along with their password.
    """

    def _get_users(self, user_model, username):
        """
        Query for verified users with a username or linked
        email address matching the provided username value
        """
        username_field = user_model.USERNAME_FIELD
        matched_users =  user_model._default_manager.filter(
                (Q(**{username_field: username})) |
                (Q(uniauth_profile__linked_emails__address__iexact=username) &
                    Q(uniauth_profile__linked_emails__is_verified=True))
        ).all()
        return filter(lambda x: not is_tmp_user(x), matched_users)
