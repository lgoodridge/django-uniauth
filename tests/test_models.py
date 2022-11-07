from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import override_settings, TestCase
from django.utils import timezone
from uniauth.models import Institution, InstitutionAccount, LinkedEmail, \
        UserProfile


class ModelSignalTests(TestCase):
    """
    Tests that the custom model signals fire and
    behave as expected
    """

    def test_create_user_profile_signal(self):
        """
        Ensure a UserProfile is automatically created
        whenever Users are
        """
        user = User.objects.create(username="new-user")
        self.assertTrue(UserProfile.objects.filter(
                user__username="new-user").exists())
        user2 = User.objects.create(username="testusr@example.com",
                email="test.user@example.com")
        self.assertTrue(UserProfile.objects.filter(
                user__email="test.user@example.com").exists())

    @override_settings(PASSWORD_RESET_TIMEOUT_DAYS=4)
    def test_clear_old_tmp_users_signal(self):
        """
        Ensure old temporary users are deleted whenever
        a new User is created
        """
        User.objects.all().delete()
        User.objects.create(username="not-temporary-user")
        for i in range(10):
            User.objects.create(username="tmp-%d-days-ago"%i)
        # We must update the date_joined in a different for loop,
        # because otherwise, the users could get deleted on the
        # create signal we're trying to test!
        for i in range(10):
            date_joined = timezone.now() - timedelta(days=i)
            user = User.objects.get(username="tmp-%d-days-ago"%i)
            user.date_joined = date_joined
            user.save()
        # Create another object to (hopefully) trigger the tmp
        # user deletion signal
        User.objects.create(username="another-user")

        expected_num_users = 10 - (settings.PASSWORD_RESET_TIMEOUT_DAYS + 1) + 2
        self.assertEqual(User.objects.count(), expected_num_users)
        self.assertTrue(User.objects.filter(username="not-temporary-user")\
                .exists())
        self.assertTrue(User.objects.filter(username="another-user").exists())
        for i in range(settings.PASSWORD_RESET_TIMEOUT_DAYS + 1):
            self.assertTrue(User.objects.filter(username="tmp-%d-days-ago"%i)\
                    .exists())
        for i in range(settings.PASSWORD_RESET_TIMEOUT_DAYS + 1, 10):
            self.assertFalse(User.objects.filter(username="tmp-%d-days-ago"%i)\
                    .exists())


class UserProfileModelTests(TestCase):
    """
    Tests the UserProfile model in models.py
    """

    def test_user_profile_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        user = User.objects.create(username="new-user")
        self.assertNotEqual(user.uniauth_profile, None)
        self.assertEqual(user.uniauth_profile.user, user)
        self.assertEqual(str(user.uniauth_profile), "new-user")
        user2 = User.objects.create(username="other-user",
                email="other@gmail.com")
        self.assertEqual(str(user2.uniauth_profile), "other@gmail.com")
        result = UserProfile.objects.get(user__username="new-user")
        self.assertEqual(result, user.uniauth_profile)
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create()

    def test_user_profile_get_display_id(self):
        """
        Ensure the get_display_id method works properly
        """
        user = User.objects.create(username="new-user")
        self.assertEqual(user.uniauth_profile.get_display_id(), "new-user")
        user = User.objects.create(username="cas-example-inst-id123")
        self.assertEqual(user.uniauth_profile.get_display_id(), "id123")
        user = User.objects.create(username="john.doe@example.com",
                email="otheraddress@example.com")
        self.assertEqual(user.uniauth_profile.get_display_id(), "john.doe")


class LinkedEmailModelTests(TestCase):
    """
    Tests the LinkedEmail model in models.py
    """

    def test_linked_email_model_basic(self):
        """
        Ensure the basic model methods + attributes work properly
        """
        user = User.objects.create(username="new-user")
        linked_email = LinkedEmail.objects.create(profile=user.uniauth_profile,
                address="example@gmail.com", is_verified=True)
        self.assertEqual(linked_email.profile, user.uniauth_profile)
        self.assertEqual(linked_email.address, "example@gmail.com")
        self.assertTrue(linked_email.is_verified)
        self.assertTrue("new-user" in str(linked_email))
        self.assertTrue("example@gmail.com" in str(linked_email))
        result = LinkedEmail.objects.get(profile=user.uniauth_profile,
                address="example@gmail.com")
        self.assertEqual(result, linked_email)

    def test_linked_email_model_clean(self):
        """
        Ensure the model prevents saving invalid states
        """
        user1 = User.objects.create(username="new-user-1")
        user2 = User.objects.create(username="new-user-2")
        user3 = User.objects.create(username="new-user-3")

        # Don't allow shared emails if setting is False
        with self.settings(UNIAUTH_ALLOW_SHARED_EMAILS=False):
            LinkedEmail.objects.create(profile=user1.uniauth_profile,
                    address="shared@example.com", is_verified=True)
            try:
                email = LinkedEmail(profile=user2.uniauth_profile,
                        address="shared@example.com", is_verified=True)
                email.clean()
                email.save()
                self.fail("Adding shared email address succeeded when "
                        "UNIAUTH_ALLOW_SHARED_EMAILS was False.")
            except ValidationError:
                pass
            self.assertFalse(LinkedEmail.objects.filter(
                    profile=user2.uniauth_profile,
                    address="shared@example.com").exists())

        # Don't allow more than the max number of linked emails per profile
        with self.settings(UNIAUTH_MAX_LINKED_EMAILS=5):
            for i in range(settings.UNIAUTH_MAX_LINKED_EMAILS):
                LinkedEmail.objects.create(profile=user3.uniauth_profile,
                        address="email%d@example.com"%i, is_verified=(i%2==0))
            try:
                email = LinkedEmail(profile=user3.uniauth_profile,
                        address="another@example.com")
                email.clean()
                email.save()
                self.fail("Able to link more than UNIAUTH_MAX_LINKED_EMAILS")
            except ValidationError:
                pass
            self.assertFalse(LinkedEmail.objects.filter(profile=user3.uniauth_profile,
                    address="another@example.com").exists())

        # Allow any number of linked emails if setting is <= 0
        with self.settings(UNIAUTH_MAX_LINKED_EMAILS=-1):
            for i in range(100):
                email, _ = LinkedEmail.objects.get_or_create(
                        profile=user3.uniauth_profile,
                        address="email%d@example.com"%i, is_verified=(i%2==0))
                email.clean()
                email.save()
            self.assertEqual(LinkedEmail.objects.filter(
                    profile=user3.uniauth_profile).count(), 100)


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
        result = Institution.objects.get(slug="test-inst")
        self.assertEqual(result, institution)
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
        account = InstitutionAccount.objects.create(
                profile=user.uniauth_profile,
                institution=institution, cas_id="netid123")
        self.assertEqual(account.profile, user.uniauth_profile)
        self.assertEqual(account.institution, institution)
        self.assertEqual(account.cas_id, "netid123")
        self.assertTrue("test-inst" in str(account))
        self.assertTrue("new-user" in str(account))
        result = InstitutionAccount.objects.get(institution=institution,
                cas_id="netid123")
        self.assertEqual(result, account)

    def test_institution_account_uniqueness_constraint(self):
        """
        Ensure creating multiple InstitutionAccounts with the same
        institution and cas_id fails
        """
        user1 = User.objects.create(username="new-user")
        user2 = User.objects.create(username="other-user")
        institution = Institution.objects.create(name="Test Inst",
                slug="test-inst", cas_server_url="https://fed.example.edu/")
        cas_id = "netid123"
        InstitutionAccount.objects.create(
                profile=user1.uniauth_profile,
                institution=institution, cas_id=cas_id)
        with self.assertRaises(IntegrityError):
            InstitutionAccount.objects.create(
                    profile=user2.uniauth_profile,
                    institution=institution, cas_id=cas_id)
