from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings, TestCase
from uniauth.models import Institution
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
        actual = Institution.objects.order_by("slug")
        expected = [
                Institution(name="Other Inst", slug="other-inst",
                    cas_server_url="http://fed.foobar.edu/"),
                Institution(name="Test", slug="test",
                    cas_server_url="https://www.example.com"),
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

