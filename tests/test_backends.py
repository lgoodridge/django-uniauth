from django.contrib.auth.models import User
from django.test import override_settings, RequestFactory, TestCase
from uniauth.backends import CASBackend, LinkedEmailBackend, \
        UsernameOrLinkedEmailBackend
from uniauth.models import Institution, InstitutionAccount, LinkedEmail
try:
    import mock
except ImportError:
    from unittest import mock


class CASBackendTests(TestCase):
    """
    Tests the CASBackend in backends.py
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.inst = Institution.objects.create(name="Test Inst",
                slug="test-inst", cas_server_url="https://fed.testinst.edu/")
        self.inst2 = Institution.objects.create(name="Other Inst",
                slug="other-inst", cas_server_url="https://fed.other.edu/")

    def _get_request(self):
        request = self.factory.get("/accounts/cas-login/")
        request.session = {}
        return request

    @mock.patch("cas.CASClientV2.verify_ticket")
    def test_cas_backend_verification_failed(self, mock_verify_ticket):
        """
        Ensure backend returns None if the ticket fails to verify
        """
        mock_verify_ticket.return_value = (None, {}, None)
        backend = CASBackend()
        request = self._get_request()

        prev_num_users = User.objects.count()
        user = backend.authenticate(request, institution=self.inst,
                ticket="fake-ticket", service="http://www.service.com/")
        self.assertEqual(user, None)
        self.assertEqual(User.objects.count(), prev_num_users)

    @mock.patch("cas.CASClientV2.verify_ticket")
    def test_cas_backend_create_user(self, mock_verify_ticket):
        """
        Ensure backend properly creates a new user when necessary
        """
        mock_verify_ticket.return_value = ("newuser", {"ticket": "fake-ticket",
            "service": "http://www.service.com/"}, None)
        backend = CASBackend()
        request = self._get_request()

        self.assertFalse(User.objects.filter(username="newuser").exists())
        prev_num_users = User.objects.count()
        user = backend.authenticate(request, institution=self.inst,
                ticket="fake-ticket", service="http://www.service.com/")
        self.assertNotEqual(user, None)
        self.assertEqual(User.objects.count(), prev_num_users+1)
        self.assertTrue(User.objects.filter(username="cas-test-inst-newuser")\
                .exists())
        self.assertEqual(request.session["attributes"],
                {"ticket": "fake-ticket", "service": "http://www.service.com/"})

    @mock.patch("cas.CASClientV2.verify_ticket")
    def test_cas_backend_existing_user(self, mock_verify_ticket):
        """
        Ensure backend returns existing user if possible
        """
        backend = CASBackend()
        user1 = User.objects.create(username="johndoe@gmail.com",
                email="john.doe@aol.com")
        InstitutionAccount.objects.create(profile=user1.uniauth_profile,
                institution=self.inst, cas_id="john123")
        user2 = User.objects.create(username="cas-test-inst-jane987")
        fakeout = User.objects.create(username="fakeout@gmail.com",
                email="fakeout@verizon.net")
        InstitutionAccount.objects.create(profile=fakeout.uniauth_profile,
                institution=self.inst2, cas_id="john123")
        prev_num_users = User.objects.count()

        # Test case where there is a user with an InstitutionAccount
        mock_verify_ticket.return_value = ("john123", {"ticket": "fake-ticket",
            "service": "http://www.example.com/"}, None)
        request = self._get_request()
        user = backend.authenticate(request, institution=self.inst,
                ticket="fake-ticket", service="http://www.example.com/")
        self.assertNotEqual(user, None)
        self.assertEqual(user.username, "johndoe@gmail.com")
        self.assertEqual(User.objects.count(), prev_num_users)
        self.assertEqual(request.session["attributes"],
                {"ticket": "fake-ticket", "service": "http://www.example.com/"})

        # Test case where there is an existing unlinked account user
        mock_verify_ticket.return_value = ("jane987", {"ticket": "ticket0123",
            "service": "http://someservice.gov/"}, None)
        request = self._get_request()
        user = backend.authenticate(request, institution=self.inst,
                ticket="ticket0123", service="http://someservice.gov/")
        self.assertNotEqual(user, None)
        self.assertEqual(user.username, "cas-test-inst-jane987")
        self.assertEqual(User.objects.count(), prev_num_users)
        self.assertEqual(request.session["attributes"],
                {"ticket": "ticket0123", "service": "http://someservice.gov/"})

    @mock.patch("cas.CASClientV2.verify_ticket")
    def test_cas_backend_missing_request(self, mock_verify_ticket):
        """
        Ensure authentication still works without the request parameter
        """
        backend = CASBackend()

        # Test creating a new user
        mock_verify_ticket.return_value = ("newuser", {"ticket": "fake-ticket",
            "service": "http://www.service.com/"}, None)
        self.assertFalse(User.objects.filter(username="newuser").exists())
        prev_num_users = User.objects.count()
        user = backend.authenticate(None, institution=self.inst,
                ticket="fake-ticket", service="http://www.service.com/")
        self.assertNotEqual(user, None)
        self.assertEqual(User.objects.count(), prev_num_users+1)
        self.assertTrue(User.objects.filter(username="cas-test-inst-newuser")\
                .exists())

        # Test finding an existing user
        mock_verify_ticket.return_value = ("jane987", {"ticket": "ticket0123",
            "service": "http://someservice.gov/"}, None)
        User.objects.create(username="cas-test-inst-jane987")
        prev_num_users = User.objects.count()
        user = backend.authenticate(None, institution=self.inst,
                ticket="ticket0123", service="http://someservice.gov/")
        self.assertNotEqual(user, None)
        self.assertEqual(user.username, "cas-test-inst-jane987")
        self.assertEqual(User.objects.count(), prev_num_users)

        # Test failed authentication
        mock_verify_ticket.return_value = (None, {}, None)
        prev_num_users = User.objects.count()
        user = backend.authenticate(None, institution=self.inst,
                ticket="fake-ticket", service="http://www.service.com/")
        self.assertEqual(user, None)
        self.assertEqual(User.objects.count(), prev_num_users)


class EmailBackendTests(TestCase):
    """
    Parent class for the *EmailBackendTests
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.john = User.objects.create_user(username="johndoe@gmail.com",
                email="johndoe@gmail.com", password="johnpass")
        self.mary = User.objects.create_user(username="marysue@outlook.com",
                email="mary.sue@gmail.com", password="marypass")
        LinkedEmail.objects.create(profile=self.mary.uniauth_profile,
                address="alternate@gmail.com", is_verified=True)
        LinkedEmail.objects.create(profile=self.mary.uniauth_profile,
                address="pending@gmail.com", is_verified=False)
        self.cas = User.objects.create_user(username="cas-inst-netid123")
        self.tmp = User.objects.create_user(username="tmp-0123_456",
                password="tmppass")
        self.perm = User.objects.create_user(username="permid555",
                password="permpass")
        self.mr = User.objects.create_user(username="mrjones@gmail.com",
                email="mrjones@gmail.com", password="mrpass")
        self.ms = User.objects.create_user(username="msjones@gmail.com",
                email="msjones@gmail.com", password="mspass")
        LinkedEmail.objects.create(profile=self.mr.uniauth_profile,
                address="sharedjones@gmail.com", is_verified=True)
        LinkedEmail.objects.create(profile=self.ms.uniauth_profile,
                address="sharedjones@gmail.com", is_verified=True)


@override_settings(UNIAUTH_ALLOW_SHARED_EMAILS=True)
class LinkedEmailBackendTests(EmailBackendTests):
    """
    Tests the LinkedEmailBackend in backends.py
    """

    def test_linked_email_backend_valid_credentials(self):
        """
        Ensure backend returns appropriate user when valid
        credentials are provided
        """
        backend = LinkedEmailBackend()

        # Log in with email + password
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="johnpass")
        self.assertEqual(user, self.john)

        # Log in with email (under "username" parameter) + password
        user = backend.authenticate(None, username="mary.sue@gmail.com",
                password="marypass")
        self.assertEqual(user, self.mary)

        # Log in with verified linked email
        user = backend.authenticate(None, email="alternate@gmail.com",
                password="marypass")
        self.assertEqual(user, self.mary)

        # Log in with shared email address
        user = backend.authenticate(None, email="sharedjones@gmail.com",
                password="mspass")
        self.assertEqual(user, self.ms)
        user = backend.authenticate(None, email="sharedjones@gmail.com",
                password="mrpass")
        self.assertEqual(user, self.mr)

    def test_linked_email_backend_invalid_credentials(self):
        """
        Ensure authentication fails when invalid credentials
        are provided
        """
        backend = LinkedEmailBackend()

        # Can't log in without username or email parameter
        user = backend.authenticate(None)
        self.assertEqual(user, None)
        user = backend.authenticate(self.factory.get("/accounts/login/"))
        self.assertEqual(user, None)

        # Can't log in with incorrect username / email
        user = backend.authenticate(None, username="dne",
                password="johnpass")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="dne@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in with no password
        user = backend.authenticate(None, username="cas-inst-netid123")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com")
        self.assertEqual(user, None)

        # Can't log in with incorrect password
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password=None)
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in with username
        user = backend.authenticate(None, email="marysue@outlook.com",
                password="marypass")
        self.assertEqual(user, None)
        user = backend.authenticate(None, username="permid555",
                password="permpass")
        self.assertEqual(user, None)

        # Can't log in with unverified email
        user = backend.authenticate(None, email="pending@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in as a temporary user
        user = backend.authenticate(None, username="tmp-0123_456",
                password="tmppass")
        self.assertEqual(user, None)


@override_settings(UNIAUTH_ALLOW_SHARED_EMAILS=True)
class UsernameOrLinkedEmailBackendTests(EmailBackendTests):
    """
    Tests the UsernameOrLinkedEmailBackend in backends.py
    """

    def test_username_orlinked_email_backend_valid_credentials(self):
        """
        Ensure backend returns appropriate user when valid
        credentials are provided
        """
        backend = UsernameOrLinkedEmailBackend()

        # Log in with email + password
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="johnpass")
        self.assertEqual(user, self.john)

        # Log in with email (under "username" parameter) + password
        user = backend.authenticate(None, username="mary.sue@gmail.com",
                password="marypass")
        self.assertEqual(user, self.mary)

        # Log in with verified linked email
        user = backend.authenticate(None, email="alternate@gmail.com",
                password="marypass")
        self.assertEqual(user, self.mary)

        # Log in with shared email address
        user = backend.authenticate(None, email="sharedjones@gmail.com",
                password="mspass")
        self.assertEqual(user, self.ms)
        user = backend.authenticate(None, email="sharedjones@gmail.com",
                password="mrpass")
        self.assertEqual(user, self.mr)

        # Log in with username
        user = backend.authenticate(None, email="marysue@outlook.com",
                password="marypass")
        self.assertEqual(user, self.mary)
        user = backend.authenticate(None, username="permid555",
                password="permpass")
        self.assertEqual(user, self.perm)

    def test_username_or_linked_email_backend_invalid_credentials(self):
        """
        Ensure authentication fails when invalid credentials
        are provided
        """
        backend = UsernameOrLinkedEmailBackend()

        # Can't log in without username or email parameter
        user = backend.authenticate(None)
        self.assertEqual(user, None)
        user = backend.authenticate(self.factory.get("/accounts/login/"))
        self.assertEqual(user, None)

        # Can't log in with incorrect username / email
        user = backend.authenticate(None, username="dne",
                password="johnpass")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="dne@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in with no password
        user = backend.authenticate(None, username="cas-inst-netid123")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com")
        self.assertEqual(user, None)

        # Can't log in with incorrect password
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password=None)
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="")
        self.assertEqual(user, None)
        user = backend.authenticate(None, email="johndoe@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in with unverified email
        user = backend.authenticate(None, email="pending@gmail.com",
                password="marypass")
        self.assertEqual(user, None)

        # Can't log in as a temporary user
        user = backend.authenticate(None, username="tmp-0123_456",
                password="tmppass")
        self.assertEqual(user, None)
