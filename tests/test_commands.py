from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings, TestCase
from uniauth.models import LinkedEmail, Institution, UserProfile
import os
import sys
try:
    import mock
except ImportError:
    from unittest import mock


class AddInstitutionCommandTests(TestCase):
    """
    Tests the add_institution management command
    """

    def setUp(self):
        Institution.objects.all().delete()
        sys.stdout = open(os.devnull, 'w')

    def _check_institutions(self, actual, expected):
        act_values = [(x.name, x.slug, x.cas_server_url) for x in actual]
        exp_values = [(x.name, x.slug, x.cas_server_url) for x in expected]
        self.assertEqual(act_values, exp_values)

    def test_add_institution_command_valid_inputs(self):
        """
        Ensures command works as expected for valid inputs
        """
        call_command("add_institution", "Test", "https://www.example.com")
        call_command("add_institution", "Other Inst", "http://fed.foobar.edu/")
        call_command("add_institution", "Test", "https://www.example.com",
            "--update-existing")
        actual = Institution.objects.order_by("slug")
        expected = [
                Institution(name="Other Inst", slug="other-inst",
                    cas_server_url="http://fed.foobar.edu/"),
                Institution(name="Test", slug="test",
                    cas_server_url="https://www.example.com"),
        ]
        self._check_institutions(actual, expected)

    def test_add_institution_command_update_existing_valid_inputs(self):
        """
        Ensures command works as expected for valid inputs with the
        --update-existing option.
        """
        call_command("add_institution", "Test", "https://www.example.com",
            "--update-existing")
        call_command("add_institution", "Other Inst", "http://fed.foobar.edu/")
        call_command("add_institution", "Test", "https://fed.university.edu/",
             "--update-existing")
        actual = Institution.objects.order_by("slug")
        expected = [
                Institution(name="Other Inst", slug="other-inst",
                    cas_server_url="http://fed.foobar.edu/"),
                Institution(name="Test", slug="test",
                    cas_server_url="https://fed.university.edu/"),
        ]
        self._check_institutions(actual, expected)

    def test_add_institution_command_invalid_inputs(self):
        """
        Ensures command fails gracefully for invalid inputs
        """
        self.assertRaisesRegex(CommandError, "argument", call_command,
                "add_institution")
        self.assertRaisesRegex(CommandError, "argument", call_command,
                "add_institution", "Some Name")
        self.assertRaisesRegex(CommandError, "malformed", call_command,
                "add_institution", "", "")
        self.assertRaisesRegex(CommandError, "malformed", call_command,
                "add_institution", "name", "https://www.example.x")
        call_command("add_institution", "Test", "https://www.example.com")
        self.assertRaisesRegex(CommandError, "exists", call_command,
                "add_institution", "test", "https://www.foo.bar")


class FlushTmpUsersTests(TestCase):
    """
    Tests the flush_tmp_users management command
    """

    @mock.patch("uniauth.management.commands.flush_tmp_users.get_input")
    @mock.patch("uniauth.management.commands.flush_tmp_users.flush_old_tmp_users")
    def test_flush_tmp_users_command_correct(self, mock_flush, mock_get_input):
        """
        Ensure command works as expected given valid starting conditions
        Ensures command propagates optional arguments properly, and uses
        expected default values when optional arguments are not provided
        """
        # Ensure command fails gracefully with invalid arguments
        self.assertRaisesRegex(CommandError, "days", call_command,
                "flush_tmp_users", "dne")

        # Ensure nothing happens when the user does not agree to continue
        mock_get_input.return_value = "no"
        call_command("flush_tmp_users")
        mock_flush.assert_not_called()

        # Ensure command propagates the optional days argument properly
        mock_get_input.return_value = "yes"
        call_command("flush_tmp_users", 4)
        mock_flush.assert_called_once_with(days=4)

        # Ensure command propagates uses expected default otherwise
        call_command("flush_tmp_users")
        mock_flush.assert_called_with(days=1)


class MigrateCASCommandTests(TestCase):
    """
    Tests the migrate_cas management command
    """

    def setUp(self):
        User.objects.all().delete()
        self.ex = User.objects.create(username="exid123")
        self.john = User.objects.create(username="johndoe")
        self.mary = User.objects.create(username="marysue")
        self.adam = User.objects.create(username="adam998")
        UserProfile.objects.all().delete()
        UserProfile.objects.create(user=self.adam)
        Institution.objects.create(name="Example Inst", slug="example-inst",
                cas_server_url="https://fake.example.edu")

    @mock.patch("uniauth.management.commands.migrate_cas.get_input")
    def test_migrate_cas_command_correct(self, mock_get_input):
        """
        Ensures command works as expected given valid starting conditions
        """
        # Ensure command fails gracefully with invalid arguments
        self.assertRaisesRegex(CommandError, "argument", call_command,
                "migrate_cas")
        self.assertRaisesRegex(CommandError, "slug", call_command,
                "migrate_cas", "dne")
        # Ensure nothing happens when the user does not agree to continue
        mock_get_input.return_value = "no"
        call_command("migrate_cas", "example-inst")
        self.assertEqual(UserProfile.objects.count(), 1)
        mock_get_input.return_value = "abcde"
        call_command("migrate_cas", "example-inst")
        self.assertEqual(UserProfile.objects.count(), 1)
        # Ensure migration occurs when user does agree to continue
        mock_get_input.return_value = "yes"
        call_command("migrate_cas", "example-inst")
        self.assertEqual(UserProfile.objects.count(), 4)
        actual_usernames = User.objects.values_list("username", flat=True)
        expected_usernames = ["adam998", "cas-example-inst-exid123",
                "cas-example-inst-johndoe", "cas-example-inst-marysue"]
        self.assertEqual(sorted(actual_usernames), expected_usernames)


class MigrateCustomCommandTests(TestCase):
    """
    Tests the migrate_custom management command
    """

    def setUp(self):
        User.objects.all().delete()
        self.ex = User.objects.create(username="exid123")
        self.john = User.objects.create(username="johndoe",
                password="johnpass")
        self.mary = User.objects.create(username="marysue",
                email="mary.sue@gmail.com", password="marypass")
        self.adam = User.objects.create(username="adam998@example.com",
                email="adam998@example.com", password="adampass")
        UserProfile.objects.all().delete()
        UserProfile.objects.create(user=self.adam)
        LinkedEmail.objects.all().delete()

    @mock.patch("uniauth.management.commands.migrate_custom.get_input")
    def test_migrate_custom_command_correct(self, mock_get_input):
        """
        Ensures command works as expected given valid starting conditions
        """
        # Ensure nothing happens when the user does not agree to continue
        mock_get_input.return_value = "no"
        call_command("migrate_custom")
        self.assertEqual(UserProfile.objects.count(), 1)
        mock_get_input.return_value = "abcde"
        call_command("migrate_custom")
        self.assertEqual(UserProfile.objects.count(), 1)
        # Ensure migration occurs when user does agree to continue
        mock_get_input.return_value = "yes"
        call_command("migrate_custom")
        self.assertEqual(UserProfile.objects.count(), 3)
        self.assertTrue(UserProfile.objects.filter(user__username="johndoe")\
                .exists())
        self.assertEqual(LinkedEmail.objects.count(), 1)
        self.assertTrue(LinkedEmail.objects.filter(address="mary.sue@gmail.com",
                profile__user__username="marysue").exists())
        self.assertEqual(self.john.uniauth_profile.linked_emails.count(), 0)


class RemoveInsitutionCommandTests(TestCase):
    """
    Tests the remove_institution management command
    """

    def setUp(self):
        Institution.objects.all().delete()
        Institution.objects.create(name="Harvard", slug="harvard",
                cas_server_url="https://fake.harvardcas.edu/")
        Institution.objects.create(name="Yale", slug="yale",
                cas_server_url="https://fake.yalecas.edu/")
        Institution.objects.create(name="Penn State", slug="penn-state",
                cas_server_url="https://fake.penncas.edu/")
        sys.stdout = open(os.devnull, 'w')

    def _check_institutions(self, actual, expected):
        act_values = [(x.name, x.slug, x.cas_server_url) for x in actual]
        exp_values = [(x.name, x.slug, x.cas_server_url) for x in expected]
        self.assertEqual(act_values, exp_values)

    @mock.patch("uniauth.management.commands.remove_institution.get_input")
    def test_remove_institution_command_valid_inputs(self, mock_get_input):
        """
        Ensures command works as expected for valid inputs
        """
        mock_get_input.return_value = "yes"
        call_command("remove_institution", "penn-state")
        mock_get_input.return_value = "y"
        call_command("remove_institution", "harvard")
        mock_get_input.return_value = "n"
        call_command("remove_institution", "yale")
        mock_get_input.return_value = "other"
        call_command("remove_institution", "yale")
        actual = Institution.objects.order_by("slug")
        expected = [Institution(name="Yale", slug="yale",
                cas_server_url="https://fake.yalecas.edu/")]
        self._check_institutions(actual, expected)

    @mock.patch("uniauth.management.commands.remove_institution.get_input")
    def test_remove_institution_command_invalid_inputs(self, mock_get_input):
        """
        Ensures command fails gracefully for invalid inputs
        """
        self.assertRaisesRegex(CommandError, "argument", call_command,
                "remove_institution")
        self.assertRaisesRegex(CommandError, "slug", call_command,
                "remove_institution", "dne")
        mock_get_input.return_value = "yes"
        call_command("remove_institution", "yale")
        self.assertRaisesRegex(CommandError, "exists", call_command,
                "remove_institution", "yale")
        actual = Institution.objects.order_by("slug")
        expected = [
                Institution(name="Harvard", slug="harvard",
                        cas_server_url="https://fake.harvardcas.edu/"),
                Institution(name="Penn State", slug="penn-state",
                        cas_server_url="https://fake.penncas.edu/")
        ]
        self._check_institutions(actual, expected)

