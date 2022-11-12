from django.test import TestCase, override_settings


class SimpleTestCase(TestCase):
    """
    Tests that the testing framework itself is setup appropiately
    """

    def test_simple(self):
        """
        Ensure the assert statements work as expected
        """
        self.assertTrue(True, "True is not True?!")
        self.assertFalse(False, "False is not False?!")

    def test_imports(self):
        """
        Ensure we can import uniauth + third party dependencies
        """
        import requests
        from cas import CASClient

        from uniauth.models import UserProfile

        user = UserProfile()
        self.assertTrue(user is not None)

    @override_settings(LOGIN_URL="/simple/login/")
    def test_settings(self):
        """
        Ensure the test settings module works as expected
        """
        from django.conf import settings

        self.assertTrue(settings.TESTING)
        self.assertEqual(settings.LOGIN_URL, "/simple/login/")
        with self.settings(UNIAUTH_LOGIN_DISPLAY_STANDARD=False):
            self.assertFalse(settings.UNIAUTH_LOGIN_DISPLAY_STANDARD)
