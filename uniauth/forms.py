from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import (
    PasswordChangeForm as AuthPasswordChangeForm,
)
from django.contrib.auth.forms import (
    PasswordResetForm as AuthPasswordResetForm,
)
from django.contrib.auth.forms import SetPasswordForm as AuthSetPasswordForm
from django.contrib.auth.forms import UserCreationForm

try:
    from django.utils.translation import ugettext_lazy as _
except ImportError:
    from django.utils.translation import gettext_lazy as _

from uniauth.models import LinkedEmail
from uniauth.utils import get_setting


class AddLinkedEmailForm(forms.Form):
    """
    Form for adding a linked email address to a profile.
    """

    email = forms.EmailField(max_length=254, label="Email address")

    def __init__(self, user, *args, **kwargs):
        super(AddLinkedEmailForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        """
        Ensures you can't link an email that has already
        been linked to the current Uniauth profile.

        If UNIAUTH_ALLOW_SHARED_EMAILS is False, ensures
        the email hasn't been linked to any profile.
        """
        email = self.cleaned_data.get("email")
        if LinkedEmail.objects.filter(
            profile=self.user.uniauth_profile, address=email
        ).exists():
            err_msg = (
                "That email address has already been linked "
                "to this account."
            )
            raise forms.ValidationError(err_msg, code="already_linked")
        if (
            not get_setting("UNIAUTH_ALLOW_SHARED_EMAILS")
            and LinkedEmail.objects.filter(
                address=email, is_verified=True
            ).exists()
        ):
            err_msg = (
                "That email address has already been linked "
                "to another account."
            )
            raise forms.ValidationError(err_msg, code="already_linked")
        return email

    def clean(self):
        """
        Ensure the user does not link more than the
        maximum number of linked emails per user.
        """
        cleaned_data = super(AddLinkedEmailForm, self).clean()
        max_linked_emails = get_setting("UNIAUTH_MAX_LINKED_EMAILS")
        num_linked_emails = self.user.uniauth_profile.linked_emails.count()
        if max_linked_emails > 0 and num_linked_emails >= max_linked_emails:
            err_msg = (
                "You can not link more than %d emails to your account."
                % max_linked_emails
            )
            raise forms.ValidationError(err_msg, code="max_emails")
        return cleaned_data


class ChangePrimaryEmailForm(forms.Form):
    """
    Form for changing a user's primary email address.
    """

    def __init__(self, user, *args, **kwargs):
        """
        Set the choices to the current profile's verified linked emails.
        """
        super(ChangePrimaryEmailForm, self).__init__(*args, **kwargs)
        self.user = user
        verified_emails = LinkedEmail.objects.filter(
            profile=self.user.uniauth_profile, is_verified=True
        ).all()
        choices = map(lambda x: (x.address, x.address), verified_emails)
        self.fields["email"] = forms.ChoiceField(choices=choices)
        self.fields["email"].initial = self.user.email

    def clean_email(self):
        """
        Ensures you can't set your primary email address to one
        another verified user already has their primary email.
        """
        email = self.cleaned_data.get("email")
        if (
            get_user_model()
            .objects.filter(email=email)
            .exclude(pk=self.user.pk)
            .exists()
        ):
            err_msg = (
                "A user with that primary email address already "
                "exists. Please choose another."
            )
            raise forms.ValidationError(err_msg, code="email_taken")
        return email


class LinkedEmailActionForm(forms.Form):
    """
    Form for deleting linked emails or resending
    verification emails for pending linked emails.
    """

    delete_pk = forms.IntegerField(required=False)
    resend_pk = forms.IntegerField(required=False)


class LoginForm(AuthenticationForm):
    """
    Form for logging via Uniauth credentials.

    Subclasses AuthenticationForm, which has username
    and password fields + some additional conveniences.

    Note: The email address field is left as 'username'
    so we can leverage the built-in methods that depend
    on it being named 'username'.
    """

    def __init__(self, request=None, *args, **kwargs):
        """
        Change the invalid login error message to mention
        using a correct email address instead of username.
        """
        super(LoginForm, self).__init__(request, *args, **kwargs)
        self.error_messages["invalid_login"] = _(
            "Please enter a correct email and password."
        )


def _prevent_shared_email_and_password(linked_emails, new_password):
    """
    Ensures the proposed new password is different from all
    passwords used by users that have a linked email in the
    provided list.
    """
    users_with_shared_email = set()

    # Get the set of users who share an email with this user
    for linked_email in linked_emails:
        users = (
            get_user_model()
            .objects.filter(
                uniauth_profile__linked_emails__address__iexact=linked_email,
                uniauth_profile__linked_emails__is_verified=True,
                is_active=True,
            )
            .all()
        )
        users_with_shared_email.update(users)

    # Make sure the new password doesn't match any of theirs
    for user in users_with_shared_email:
        if user.check_password(new_password):
            err_msg = "Please choose a different password."
            raise forms.ValidationError(err_msg, code="password_taken")

    return new_password


class SetPasswordForm(AuthSetPasswordForm):
    """
    Form allowing a user to change their password without
    entering their old one.

    Subclasses the built-in SetPasswordForm, which does
    most of the heavy lifting + has several security features.
    """

    def clean_new_password1(self):
        """
        Prevent users from setting their password to the same
        password another user with a shared linked email is using.
        """
        new_password = self.cleaned_data.get("new_password1")
        linked_emails = self.user.uniauth_profile.linked_emails.values_list(
            "address", flat=True
        )
        _prevent_shared_email_and_password(linked_emails, new_password)
        return new_password


class PasswordChangeForm(AuthPasswordChangeForm):
    """
    Form allowing a user to change their password by entering
    their old one first.

    Subclasses the built-in PasswordChangeForm, which does
    most of the heavy lifting + has several security features.
    """

    def clean_new_password1(self):
        """
        Prevent users from setting their password to the same
        password another user with a shared linked email is using.
        """
        new_password = self.cleaned_data.get("new_password1")
        linked_emails = self.user.uniauth_profile.linked_emails.values_list(
            "address", flat=True
        )
        _prevent_shared_email_and_password(linked_emails, new_password)
        return new_password


class PasswordResetForm(AuthPasswordResetForm):
    """
    Form for asking for a password reset.

    Subclasses the built-in PasswordResetForm, which does
    most of the heavy lifting + has several security features.
    """

    def get_users(self, email):
        """
        Given an email, returns matching user(s) who should
        receive a password reset link.

        Modified to find all users who possess the provided
        address as a verified linked email instead of just
        primary email.
        """
        users = get_user_model().objects.filter(
            uniauth_profile__linked_emails__address__iexact=email,
            uniauth_profile__linked_emails__is_verified=True,
            is_active=True,
        )
        return (u for u in users if u.has_usable_password())


class SignupForm(UserCreationForm):
    """
    Form for creating a new Uniauth account.

    Subclasses UserCreationForm, which has two password fields
    (one is for confirming it) + some additional conveniences.
    """

    email = forms.EmailField(
        max_length=254,
        label="Email address",
        help_text="Primary email address.",
    )

    class Meta:
        model = get_user_model()
        fields = ("email", "password1", "password2")

    def clean_email(self):
        """
        Ensures that you can't sign up with an email address
        another verified user already has their primary email.

        If UNIAUTH_ALLOW_SHARED_EMAILS is False, ensures the
        email hasn't been linked + verified by any profile.
        """
        email = self.cleaned_data.get("email")
        if get_user_model().objects.filter(email=email).exists():
            err_msg = (
                "A user with that primary email address already "
                "exists. Please choose another."
            )
            raise forms.ValidationError(err_msg, code="email_taken")
        if (
            not get_setting("UNIAUTH_ALLOW_SHARED_EMAILS")
            and LinkedEmail.objects.filter(
                address=email, is_verified=True
            ).exists()
        ):
            err_msg = (
                "That email address has already been linked "
                "to another account."
            )
            raise forms.ValidationError(err_msg, code="already_linked")
        return email

    def clean_password1(self):
        """
        Prevent users from setting their password to the same
        password another user with a shared linked email is using.
        """
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password1")
        _prevent_shared_email_and_password([email], password)
        return password
