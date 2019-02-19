from django.contrib.auth.models import User
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import override_settings, TestCase
from uniauth.models import Institution, InstitutionAccount, LinkedEmail, \
        UserProfile


class UserProfileModelTests(TestCase):
    """
    Tests the UserProfile model in models.py
    """

    def test_user_profile_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        user = User.objects.create(username="new-user")
        self.assertNotEqual(user.profile, None)
        self.assertEqual(user.profile.user, user)
        self.assertEqual(str(user.profile), "new-user")
        user2 = User.objects.create(username="other-user",
                email="other@gmail.com")
        self.assertEqual(str(user2.profile), "other@gmail.com")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create()


class LinkedEmailModelTests(TestCase):
    """
    Tests the LinkedEmail model in models.py
    """

    def test_linked_email_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        user = User.objects.create(username="new-user")
        linked_email = LinkedEmail.objects.create(profile=user.profile,
                address="example@gmail.com", is_verified=True)
        self.assertEqual(linked_email.profile, user.profile)
        self.assertEqual(linked_email.address, "example@gmail.com")
        self.assertTrue(linked_email.is_verified)
        self.assertTrue("new-user" in str(linked_email))
        self.assertTrue("example@gmail.com" in str(linked_email))


class InstitutionModelTests(TestCase):
    """
    Tests the Institution model in models.py
    """

    def test_institution_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        institution = Institution.objects.create(name="Test Inst",
                slug="test-inst", cas_server_url="https://fed.example.edu/")
        self.assertEqual(institution.name, "Test Inst")
        self.assertEqual(institution.slug, "test-inst")
        self.assertEqual(institution.cas_server_url, "https://fed.example.edu/")
        self.assertEqual(str(institution), "test-inst")
        with self.assertRaises(IntegrityError):
            Institution.objects.create(name="Test-inst", slug="test-inst",
                    cas_server_url="https://www.different.edu/")


class InstitutionAccountModelTests(TestCase):
    """
    Tests the InstitutionAccount model in models.py
    """

    def test_institution_account_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        user = User.objects.create(username="new-user")
        institution = Institution.objects.create(name="Test Inst",
                slug="test-inst", cas_server_url="https://fed.example.edu/")
        account = InstitutionAccount.objects.create(profile=user.profile,
                institution=institution, cas_id="netid123")
        self.assertEqual(account.profile, user.profile)
        self.assertEqual(account.institution, institution)
        self.assertEqual(account.cas_id, "netid123")
        self.assertTrue("test-inst" in str(account))
        self.assertTrue("new-user" in str(account))

