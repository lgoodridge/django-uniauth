import json

from django.contrib.auth.models import User
from django.core import mail
from django.http import HttpResponseRedirect
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from tests.utils import assert_urls_equivalent
from uniauth.models import Institution, InstitutionAccount, LinkedEmail
from uniauth.views import (
    _add_institution_account,
    _get_global_context,
    _login_success,
    _send_verification_email,
    get_jwt_tokens_from_session,
)


class AddInstitutionAccountTests(TestCase):
    """
    Tests the _add_instituion_account method in views.py
    """

    def setUp(self):
        self.inst1 = Institution.objects.create(
            name="Test Uni",
            slug="test-uni",
            cas_server_url="https://cas.testuni.edu",
        )
        self.inst2 = Institution.objects.create(
            name="Other Inst",
            slug="other-inst",
            cas_server_url="https://fed.other-inst.edu",
        )

    def test_add_institution_account_link_succeeds(self):
        """
        Ensures the method successfully links the new
        Institution Account to the profile
        """
        user = User.objects.create(username="johndoe")
        User.objects.create(username="cas-test-uni-jd123")
        _add_institution_account(user.uniauth_profile, "test-uni", "jd123")
        linked_accounts = user.uniauth_profile.accounts.all()
        cas_user1 = User.objects.get(username="cas-test-uni-jd123")
        self.assertEqual(len(linked_accounts), 1)
        self.assertEqual(linked_accounts[0].institution, self.inst1)
        self.assertEqual(linked_accounts[0].cas_id, "jd123")

        User.objects.create(username="cas-other-inst-john.doe4")
        _add_institution_account(
            user.uniauth_profile, "other-inst", "john.doe4"
        )
        linked_accounts = user.uniauth_profile.accounts.all()
        cas_user2 = User.objects.get(username="cas-other-inst-john.doe4")
        self.assertEqual(len(linked_accounts), 2)
        self.assertEqual(linked_accounts[1].institution, self.inst2)
        self.assertEqual(linked_accounts[1].cas_id, "john.doe4")


class GetGlobalContextTests(TestCase):
    """
    Tests the _get_global_context method in views.py
    """

    def setUp(self):
        self.factory = RequestFactory()
        Institution.objects.all().delete()
        self.inst1 = Institution.objects.create(
            name="Test Uni",
            slug="test-uni",
            cas_server_url="https://cas.testuni.edu",
        )
        self.inst2 = Institution.objects.create(
            name="Other Inst",
            slug="other-inst",
            cas_server_url="https://fed.other-inst.edu",
        )

    def test_get_global_context_correct(self):
        """
        Ensure method returns the expected template context
        """
        request = self.factory.get(
            "/accounts/login/", data={"foo": "bar", "next": "/next-page/"}
        )
        result = _get_global_context(request)
        result["institutions"].sort(key=lambda x: x[0])
        expected_institutions = [
            (
                "Other Inst",
                "other-inst",
                "/accounts/cas-login/other-inst/",
                "/accounts/link-from-profile/other-inst/",
            ),
            (
                "Test Uni",
                "test-uni",
                "/accounts/cas-login/test-uni/",
                "/accounts/link-from-profile/test-uni/",
            ),
        ]
        expected_params = "?foo=bar&next=%2Fnext-page%2F"
        self.assertEqual(
            sorted(list(result.keys())), ["institutions", "query_params"]
        )
        self.assertEqual(result["institutions"], expected_institutions)
        assert_urls_equivalent(
            result["query_params"], expected_params, self.assertEqual
        )


class LoginSuccessTests(TestCase):
    """
    Tests the _login_success method in views.py
    """

    factory = RequestFactory()

    def _run_test(self, username, params_dict, expected_url):
        user = User.objects.create(username=username)
        request = self.factory.get("/test/page/", data=params_dict)
        result = _login_success(request, user, "/next-page/")
        self.assertEqual(type(result), HttpResponseRedirect)
        assert_urls_equivalent(result.url, expected_url, self.assertEqual)

    def test_login_success_correct_destination(self):
        """
        Ensure method returns the correct destination URL,
        dependent on whether the user has a temporary account
        """
        self._run_test(
            "tmp-abc123", {}, "/accounts/link-to-profile/?next=%2Fnext-page%2F"
        )
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=False):
            self._run_test(
                "cas-dashed-inst-id123",
                {},
                "/accounts/link-to-profile/?next=%2Fnext-page%2F",
            )
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=True):
            self._run_test("cas-dashed-inst-id987", {}, "/next-page/")
        self._run_test("john.doe@hmail.moc", {}, "/next-page/")

    def test_login_success_preserve_query_params(self):
        """
        Ensure outputted URL preserves query parameters
        """
        self._run_test(
            "tmp-a0b1c2",
            {"hello": "world"},
            "/accounts/link-to-profile/?hello=world&next=%2Fnext-page%2F",
        )
        self._run_test(
            "tmp-z9y8x7",
            {"foo": "bar", "next": "/detour/"},
            "/accounts/link-to-profile/?foo=bar&next=%2Fnext-page%2F",
        )
        self._run_test("example@foo.bar", {"hi": "bye"}, "/next-page/?hi=bye")
        self._run_test(
            "student@inst.edu",
            {"dead": "beef", "next": "/detour/"},
            "/next-page/?dead=beef",
        )

    @override_settings(UNIAUTH_USE_JWT_AUTH=True)
    def test_login_success_use_jwt_auth(self):
        user = User.objects.create(username="student@institution.edu")

        self.client.force_login(user)
        session = self.client.session

        response = self.client.get(reverse("uniauth:login"))

        self.assertEqual(type(response), HttpResponseRedirect)
        self.assertTrue(session["jwt-refresh"])
        self.assertTrue(session["jwt-access"])


class SendVerificationEmail(TestCase):
    """
    Tests the _send_verification_email method in views.py
    """

    factory = RequestFactory()

    @override_settings(UNIAUTH_FROM_EMAIL="uniauth@testsmtp.ml")
    def test_send_verification_email_correct(self):
        """
        Ensure the subject, to address, and from address for
        a sent verification email is correct
        """
        user = User.objects.create(username="student")
        verify_email = LinkedEmail.objects.create(
            profile=user.uniauth_profile,
            address="toverify@gmail.com",
            is_verified=False,
        )
        request = self.factory.get("/accounts/somepage/", secure=False)
        _send_verification_email(request, "student@example.edu", verify_email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("verify" in mail.outbox[0].subject.lower())
        self.assertTrue("/verify-token/" in mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["student@example.edu"])
        self.assertEqual(mail.outbox[0].from_email, "uniauth@testsmtp.ml")

        user2 = User.objects.create(username="otherstud")
        verify_email2 = LinkedEmail.objects.create(
            profile=user2.uniauth_profile,
            address="stud_2@example.edu",
            is_verified=False,
        )
        request = self.factory.get("/accounts/otherpage/", secure=True)
        _send_verification_email(request, "stud_2@example.edu", verify_email2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue("verify" in mail.outbox[1].subject.lower())
        self.assertTrue("/verify-token/" in mail.outbox[1].body)
        self.assertEqual(mail.outbox[1].to, ["stud_2@example.edu"])
        self.assertEqual(mail.outbox[1].from_email, "uniauth@testsmtp.ml")


class GetJWTTokensFromSession(TestCase):
    """
    Tests the get_jwt_tokens_from_session method in views.py
    """

    factory = RequestFactory()

    FAKE_REFRESH_TOKEN = "refresh.token.string"
    FAKE_ACCESS_TOKEN = "access.token.string"

    def _run_test(
        self,
        username,
        session_state,
        expected_response_status,
        expected_response_data,
    ):
        user = User.objects.create(username=username)
        request = self.factory.get("/jwt-tokens/", data={})
        request.user = user
        request.session = session_state
        response = get_jwt_tokens_from_session(request)
        self.assertEqual(response.status_code, expected_response_status)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")),
            expected_response_data,
        )

    def test_get_jwt_tokens_from_session(self):
        self._run_test(
            "tmp-c65433",
            {
                "jwt-refresh": self.FAKE_REFRESH_TOKEN,
                "jwt-access": self.FAKE_ACCESS_TOKEN,
            },
            200,
            {
                "refresh": self.FAKE_REFRESH_TOKEN,
                "access": self.FAKE_ACCESS_TOKEN,
            },
        )
        self._run_test(
            "tmp-a67653", {"jwt-refresh": self.FAKE_REFRESH_TOKEN}, 404, {}
        )
        self._run_test(
            "tmp-a65343", {"jwt-access": self.FAKE_ACCESS_TOKEN}, 404, {}
        )
        self._run_test("tmp-a75643", {}, 404, {})
