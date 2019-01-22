from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Creates tokens for linked email verification.
    """

    def _make_hash_value(self, email, timestamp):
        return str(email.pk) + str(email.is_verified) + str(timestamp)


token_generator = EmailVerificationTokenGenerator()
