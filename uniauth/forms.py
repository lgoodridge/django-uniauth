from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, \
        PasswordChangeForm as AuthPasswordChangeForm, \
        PasswordResetForm as AuthPasswordResetForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from uniauth.models import LinkedEmail


class AddLinkedEmailForm(forms.Form):
    """
    Form for adding a linked email address to a profile.
    """
    email = forms.EmailField(max_length=254, label="Email address")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        """
        Ensures you can't link an email that has already
        been linked to the current Uniauth profile.
        """
        email = self.cleaned_data.get('email')
        if LinkedEmail.objects.filter(profile=self.user.profile,
                address=email).exists():
            err_msg = ("That email address has already been linked "
                    "to this account.")
            raise forms.ValidationError(err_msg, code="already_linked")
        return email


class ChangePrimaryEmailForm(forms.Form):
    """
    Form for changing a user's primary email address.
    """

    def __init__(self, user, *args, **kwargs):
        """
        Set the choices to the current profile's verified linked emails.
        """
        super().__init__(*args, **kwargs)
        self.user = user
        verified_emails = LinkedEmail.objects.filter(profile=self.user.profile,
                is_verified=True).all()
        choices = map(lambda x: (x.address, x.address), verified_emails)
        self.fields['email'] = forms.ChoiceField(choices=choices)
        self.fields['email'].initial = self.user.email

    def clean_email(self):
        """
        Ensures that you can't sign up with an email address
        another verified user already has their primary email.
        """
        email = self.cleaned_data.get('email')
        if get_user_model().objects.filter(email=email)\
                .exclude(pk=self.user.pk).exists():
            err_msg = ("A user with that primary email address already "
                    "exists. Please choose another.")
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
        super().__init__(request, *args, **kwargs)
        self.error_messages['invalid_login'] = _(
                "Please enter a correct email and password."
        )


class PasswordChangeForm(AuthPasswordChangeForm):
    """
    Form allowing a user to change their password by entering
    their old one first.

    Subclasses the built-in PasswordChangeForm, which does
    most of the heavy lifting + has several security features.
    """
    pass


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
                profile__linked_emails__address__iexact=email,
                profile__linked_emails__is_verified=True,
                is_active=True
        )
        return (u for u in users if u.has_usable_password())


class SignupForm(UserCreationForm):
    """
    Form for creating a new Uniauth account.

    Subclasses UserCreationForm, which has two password fields
    (one is for confirming it) + some additional conveniences.
    """

    email = forms.EmailField(max_length=254, label="Email address",
            help_text="Primary email address.")

    class Meta:
        model = get_user_model()
        fields = ('email', 'password1', 'password2')

    def clean_email(self):
        """
        Ensures that you can't sign up with an email address
        another verified user already has their primary email.
        """
        email = self.cleaned_data.get('email')
        if get_user_model().objects.filter(email=email).exists():
            err_msg = ("A user with that primary email address already "
                    "exists. Please choose another.")
            raise forms.ValidationError(err_msg, code="email_taken")
        return email

