from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework_simplejwt.tokens import RefreshToken


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Creates tokens for linked email verification.
    """

    def _make_hash_value(self, email, timestamp):
        return str(email.pk) + str(email.is_verified) + str(timestamp)


token_generator = EmailVerificationTokenGenerator()


def get_jwt_tokens_for_user(user, **kwargs):
    """
    Generates a refresh token for the valid user
    """
    refresh = RefreshToken.for_user(user)

    return str(refresh), str(refresh.access_token)