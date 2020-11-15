from django.contrib.auth.models import AnonymousUser, User
from django.test import override_settings, RequestFactory, TestCase
from random import randint
from tests.utils import assert_urls_equivalent, pretty_str
from uniauth.utils import choose_username, decode_pk, encode_pk, \
        flush_old_tmp_users, get_account_username_split, get_random_username, \
        get_redirect_url, get_service_url, get_setting, is_tmp_user, \
        DEFAULT_SETTING_VALUES


class ChooseUsernameTests(TestCase):
    """
    Tests the choose_username method in utils.py
    """

    def test_choose_username_unique(self):
        """
        Ensure that all outputted usernames are unique
        """
        emails = [
                "fakeemail@example.com",
                "abcde@fgh.com",
                "abcd@gh.com",
                "abce@gh.com",
                "abce@gh.ijk",
                "repeat@gmail.com",
                "repeat@gmail.com",
                "repeat@gmail.com",
        ]
        usernames = []
        for email in emails:
            username = choose_username(email)
            usernames.append(username)
            User.objects.create(username=username, email=email)
        if len(set(usernames)) != len(emails):
            zip_str = pretty_str([x+": "+y for x,y in zip(emails, usernames)])
            self.fail("choose_username outputted a duplicate username.\n"
                    "Emails vs Usernames: %s" % zip_str)


class EncodeDecodePkTests(TestCase):
    """
    Tests the encode_pk and decode_pk methods in utils.py
    """

    def test_encode_decode_pk_reversible(self):
        """
        Ensure that encoding a PK, then decoding it returns
        the original value
        """
        for i in range(50):
            random_pk = randint(1, 10000)
            encoded = encode_pk(random_pk)
            decoded = decode_pk(encoded)
            if str(random_pk) != decoded:
                self.fail(("Encoding then decoding PK '%d' did not return "
                        "original value.\nEncoded: %s\tDecoded: %s") % \
                        (random_pk, encoded, decoded))


class FlushOldTmpUsersTests(TestCase):
    """
    Tests the flush_old_tmp_users method in utils.py
    """

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        self.tmp0 = User.objects.create(username="tmp-0",
                date_joined=timezone.now()-timedelta(days=0))
        self.tmp1 = User.objects.create(username="tmp-1",
                date_joined=timezone.now()-timedelta(days=1))
        self.tmp2 = User.objects.create(username="tmp-2",
                date_joined=timezone.now()-timedelta(days=2))
        self.tmp3 = User.objects.create(username="tmp-3",
                date_joined=timezone.now()-timedelta(days=3))
        self.real = User.objects.create(username="a-real-user",
                date_joined=timezone.now()-timedelta(days=3))

    def test_flush_old_tmp_users_deletes_proper_users(self):
        """
        Ensure the proper users are deleted given the days argument
        """
        num_deleted = flush_old_tmp_users(days=2)
        self.assertEqual(num_deleted, 2)
        remaining_users = User.objects.all()
        self.assertIn(self.tmp0, remaining_users)
        self.assertIn(self.tmp1, remaining_users)
        self.assertNotIn(self.tmp2, remaining_users)
        self.assertNotIn(self.tmp3, remaining_users)
        self.assertIn(self.real, remaining_users)

    def test_flush_old_tmp_users_deletes_proper_users(self):
        """
        Ensure the function uses a default days parameter if not provided
        """
        num_deleted = flush_old_tmp_users()
        self.assertEqual(num_deleted, 3)
        remaining_users = User.objects.all()
        self.assertIn(self.tmp0, remaining_users)
        self.assertNotIn(self.tmp1, remaining_users)
        self.assertNotIn(self.tmp2, remaining_users)
        self.assertNotIn(self.tmp3, remaining_users)
        self.assertIn(self.real, remaining_users)


class GetAccountUsernameSplitTests(TestCase):
    """
    Tests the get_account_username_split method in utils.py
    """

    def test_get_account_username_split_unlinked_account(self):
        """
        Ensure it works for unlinked InstitutionAccount users
        """
        def _run_test(username, expected_result):
            result = get_account_username_split(username)
            self.assertEqual(result[0], expected_result[0])
            self.assertEqual(result[1], expected_result[1])
            self.assertEqual(result[2], expected_result[2])

        _run_test("cas-princeton-netid", ("cas", "princeton", "netid"))
        _run_test("exauth-exinst-exid", ("exauth", "exinst", "exid"))
        _run_test("ab_c-long-dashed-slug-id123",
                ("ab_c", "long-dashed-slug", "id123"))
        _run_test("a-b-c", ("a", "b", "c"))
        _run_test("aa-aa-aa", ("aa", "aa", "aa"))

    def test_get_account_username_split_invalid_users(self):
        """
        Ensure it fails as expected for non unlinked account users
        """
        def _run_test(username):
            try:
                result = get_account_username_split(username)
                self.fail("get_account_username_split did not raise an "
                        "exception when provided username for a non unlinked "
                        "Institution.\n'%s' returned '%s'" % (username, result))
            except ValueError:
                pass

        _run_test("exusername")
        _run_test("tmp-abcde")
        _run_test("ex-abc_def")
        _run_test("")


class GetRandomUsernameTests(TestCase):
    """
    Tests the get_random_username method in utils.py
    """

    def test_get_random_username_valid(self):
        """
        Ensure all outputted usernames have the 'tmp' prefix
        """
        for i in range(100):
            username = get_random_username()
            if not username.startswith("tmp"):
                self.fail("get_random_username outputted a username that "
                        "did not start with 'tmp_': %s" % username)

    def test_get_random_username_unique(self):
        """
        Ensure all outputted usernames are unique
        """
        usernames = []
        for i in range(100):
            username = get_random_username()
            if username in usernames:
                self.fail("get_random_username outputted a duplicate "
                        "username: %s" % username)
            usernames.append(username)


class GetRedirectUrlTests(TestCase):
    """
    Tests the get_redirect_url method in utils.py
    """

    factory = RequestFactory()

    def test_get_redirect_url_query_parameter(self):
        """
        Ensure method returns URL provided as query parameter
        over everything else if present
        """
        request = self.factory.get("/accounts/login/",
                data={"next": "/next-page/"})
        result = get_redirect_url(request)
        self.assertEqual(result, "/next-page/")

    def test_get_redirect_url_referer(self):
        """
        Ensure method returns the referring page if use_referer
        is True, and no relevant query parameter was provided
        """
        request = self.factory.get("/accounts/cas-login/test-inst/",
                HTTP_REFERER="/home/")
        result = get_redirect_url(request, use_referer=True,
                default_url="/default/")
        self.assertEqual(result, "/home/")

    def test_get_redirect_url_defaults(self):
        """
        Ensure method uses the provided default URL or default
        login URL setting if no other options are available
        """
        request = self.factory.get("/accounts/login/", HTTP_REFERER="/home")
        result = get_redirect_url(request, use_referer=False,
                default_url="/default/")
        self.assertEqual(result, "/default/")

        request = self.factory.get("/accounts/login/", HTTP_REFERER="/home")
        result = get_redirect_url(request)
        default_login = DEFAULT_SETTING_VALUES["UNIAUTH_LOGIN_REDIRECT_URL"]
        self.assertEqual(result, default_login)


class GetServiceUrlTests(TestCase):
    """
    Tests the get_service_url method in utils.py
    """

    factory = RequestFactory()

    def test_get_service_url_correct(self):
        """
        Ensure method behaves properly when redirect_url
        is or is not provided
        """
        request = self.factory.get("/accounts/login/",
                data={"next": "/next-page/"})

        result = get_service_url(request)
        expected = "http://testserver/accounts/login/?next=%2Fnext-page%2F"
        self.assertEqual(result, expected)

        result = get_service_url(request, "/alt/target/")
        expected = "http://testserver/accounts/login/?next=%2Falt%2Ftarget%2F"
        self.assertEqual(result, expected)

    def test_get_service_url_query_parameters(self):
        """
        Ensure method preserves query parameters
        """
        request = self.factory.get("/origin/?foo=bar", secure=True)
        result = get_service_url(request, "/target/")
        expected = "https://testserver/origin/?foo=bar&next=%2Ftarget%2F"
        assert_urls_equivalent(result, expected, self.assertEqual)

        request = self.factory.get("/origin/", secure=True,
                data={"foo": "bar", "next": "/next-page/?cat=dog"})
        result = get_service_url(request)
        expected = ("https://testserver/origin/?foo=bar"
                "&next=%2Fnext-page%2F%3Fcat%3Ddog")
        assert_urls_equivalent(result, expected, self.assertEqual)

    def test_get_service_url_ignore_ticket(self):
        """
        Ensures ticket is ignored if present as query parameter
        """
        request = self.factory.get("/origin/", secure=True,
                data={"foo": "bar", "next": "/next-page/?cat=dog",
                        "ticket": "FAKE-ticket-456"})
        result = get_service_url(request)
        expected = ("https://testserver/origin/?foo=bar"
                "&next=%2Fnext-page%2F%3Fcat%3Ddog")
        assert_urls_equivalent(result, expected, self.assertEqual)


class GetSettingTests(TestCase):
    """
    Tests the get_setting method in utils.py
    """

    def test_get_setting_default_settings(self):
        """
        Ensure the default values for Uniauth's settings are
        returned when not provided in the settings file
        """
        # The test settings file does not set any Uniauth
        # settings - so everything should be the default value
        self.assertEqual(get_setting("LOGIN_URL"), "/accounts/login/")
        self.assertEqual(get_setting("PASSWORD_RESET_TIMEOUT_DAYS"), 3)
        self.assertEqual(get_setting("UNIAUTH_LOGIN_DISPLAY_STANDARD"), True)
        for setting, default_value in DEFAULT_SETTING_VALUES.items():
            self.assertEqual(get_setting(setting), default_value)

    @override_settings(LOGIN_URL="/new/login/",
            UNIAUTH_LOGIN_DISPLAY_STANDARD=False,
            UNIAUTH_MAX_LINKED_EMAILS=-11)
    def test_get_setting_provided_settings(self):
        """
        Ensure the provided values for settings are used
        when present
        """
        self.assertEqual(get_setting("LOGIN_URL"), "/new/login/")
        self.assertEqual(get_setting("UNIAUTH_LOGIN_DISPLAY_STANDARD"), False)
        self.assertEqual(get_setting("UNIAUTH_MAX_LINKED_EMAILS"), -11)
        # Should still be the default value, since it wasn't set
        self.assertEqual(get_setting("PASSWORD_RESET_TIMEOUT_DAYS"), 3)

    def test_get_setting_nonexistent_settings(self):
        """
        Ensure it fails for settings that don't exist
        """
        def _run_test(setting):
            try:
                result = get_setting(setting)
                self.fail("get_setting did not raise an exception when"
                        "asked for non-existent setting: '%s' returned '%s'"
                        % (setting, result))
            except KeyError:
                pass

        _run_test("dne")
        _run_test("UNIAUTH_FAKE_SETTING")
        _run_test("")


class IsTmpUserTests(TestCase):
    """
    Tests the is_tmp_user method in utils.py
    """

    def test_is_tmp_user_profile(self):
        """
        Ensure users with verified Uniauth profiles return False
        """
        user1 = User.objects.create(username="test@example.com")
        user2 = User.objects.create(username="abc@def.ghi_0002")
        users = [user1, user2]

        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=True):
            for user in users:
                self.assertFalse(is_tmp_user(user))
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=False):
            for user in users:
                self.assertFalse(is_tmp_user(user))

    def test_is_tmp_user_institution_account(self):
        """
        Ensure users logged in via an Insitution Account return
        True if standalone accounts aren't allowed, False otherwise
        """
        user1 = User.objects.create(username="cas-princeton-netid")
        user2 = User.objects.create(username="cas-long-dashed-slug-id123")
        users = [user1, user2]

        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=True):
            for user in users:
                self.assertFalse(is_tmp_user(user))
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=False):
            for user in users:
                self.assertTrue(is_tmp_user(user))

    def test_is_tmp_user_temporary_user(self):
        """
        Ensure users with temporary usernames return True
        """
        user1 = User.objects.create(username="tmp-example")
        user2 = User.objects.create(username="tmp-20190217200307725912_wGgOE")
        users = [user1, user2]

        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=True):
            for user in users:
                self.assertTrue(is_tmp_user(user))
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=False):
            for user in users:
                self.assertTrue(is_tmp_user(user))

    def test_is_tmp_user_unauthenticated(self):
        """
        Ensure unauthenticated users return False
        """
        user1 = User.objects.create(username="")
        user2 = AnonymousUser()
        users = [user1, user2]

        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=True):
            for user in users:
                self.assertFalse(is_tmp_user(user))
        with self.settings(UNIAUTH_ALLOW_STANDALONE_ACCOUNTS=False):
            for user in users:
                self.assertFalse(is_tmp_user(user))

