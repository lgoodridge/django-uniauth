from django.contrib.auth.models import User
from django.test import override_settings, TestCase
from uniauth.models import Institution, InstitutionAccount, LinkedEmail
from uniauth.merge import merge_model_instances


class MergeModelInstancesTests(TestCase):
    """
    Tests the merge_model_instances method in merge.py
    """

    def setUp(self):
        self.inst1 = Institution.objects.create(name="Test Uni",
                slug="test-uni", cas_server_url="https://cas.testuni.edu")
        self.inst2 = Institution.objects.create(name="Other Inst",
                slug="other-inst", cas_server_url="https://fed.other-inst.edu")

        self.user1 = User.objects.create(username="user1@example.com",
                email="user1@example.com")
        self.user2 = User.objects.create(username="cas-test-uni-user2")
        InstitutionAccount.objects.create(profile=self.user2.uniauth_profile,
                institution=self.inst1, cas_id="user2")

        self.user3 = User.objects.create(username="user3@gmail.com",
                email="user3@gmail.com")
        LinkedEmail.objects.create(profile=self.user3.uniauth_profile,
                address="backup@gmail.com")
        InstitutionAccount.objects.create(profile=self.user3.uniauth_profile,
                institution=self.inst1, cas_id="john123")
        self.user4 = User.objects.create(username="us.er4@nowhere.gov",
                email="huh@what.edu")
        LinkedEmail.objects.create(profile=self.user4.uniauth_profile,
                address="another@gmail.com", is_verified=True)
        InstitutionAccount.objects.create(profile=self.user4.uniauth_profile,
                institution=self.inst2, cas_id="exid001")
        self.user5 = User.objects.create(username="user5@foo.bar",
                email="user5@foo.bar")

    def _check_emails(self, actual, expected):
        actual_values = [(x.profile, x.address) for x in actual]
        expected_values = [(x.profile, x.address) for x in expected]
        self.assertEqual(actual_values, expected_values)

    def _check_accounts(self, actual, expected):
        act_values = [(x.profile, x.institution, x.cas_id) for x in actual]
        exp_values = [(x.profile, x.institution, x.cas_id) for x in expected]
        self.assertEqual(act_values, exp_values)

    @override_settings(UNIAUTH_PERFORM_RECURSIVE_MERGING=False)
    def test_merge_model_instances_non_recursive(self):
        """
        Ensure non-recursive merges work as expected
        """
        merge_model_instances(self.user1, [self.user2])
        self.assertTrue(User.objects.filter(username="user1@example.com")\
                .exists())
        self.assertFalse(User.objects.filter(username="cas-test-uni-user2")\
                .exists())

        merged = User.objects.get(username="user1@example.com")
        emails = list(merged.uniauth_profile.linked_emails.order_by("address"))
        accounts = list(merged.uniauth_profile.accounts.order_by("cas_id"))

        expected_emails = [
                LinkedEmail(profile=merged.uniauth_profile,
                        address="user1@example.com"),
        ]
        expected_accounts = [
        ]
        self._check_emails(emails, expected_emails)
        self._check_accounts(accounts, expected_accounts)

        merge_model_instances(self.user3, [self.user4, self.user5])
        self.assertTrue(User.objects.filter(username="user3@gmail.com")\
                .exists())
        self.assertFalse(User.objects.filter(username="us.er4@nowhere.gov")\
                .exists())
        self.assertFalse(User.objects.filter(username="user5@foo.bar")\
                .exists())

        merged = User.objects.get(username="user3@gmail.com")
        emails = list(merged.uniauth_profile.linked_emails.order_by("address"))
        accounts = list(merged.uniauth_profile.accounts.order_by("cas_id"))

        expected_emails = [
                LinkedEmail(profile=merged.uniauth_profile,
                        address="backup@gmail.com"),
                LinkedEmail(profile=merged.uniauth_profile,
                    address="user3@gmail.com"),
        ]
        expected_accounts = [
                InstitutionAccount(profile=merged.uniauth_profile,
                        institution=self.inst1, cas_id="john123"),
        ]
        self._check_emails(emails, expected_emails)
        self._check_accounts(accounts, expected_accounts)

    @override_settings(UNIAUTH_PERFORM_RECURSIVE_MERGING=True)
    def test_merge_model_instances_recursive(self):
        """
        Ensure recursive merges work as expected
        """
        merge_model_instances(self.user1, [self.user2])
        self.assertTrue(User.objects.filter(username="user1@example.com")\
                .exists())
        self.assertFalse(User.objects.filter(username="cas-test-uni-user2")\
                .exists())

        merged = User.objects.get(username="user1@example.com")
        emails = list(merged.uniauth_profile.linked_emails.order_by("address"))
        accounts = list(merged.uniauth_profile.accounts.order_by("cas_id"))

        expected_emails = [
                LinkedEmail(profile=merged.uniauth_profile,
                        address="user1@example.com"),
        ]
        expected_accounts = [
                InstitutionAccount(profile=merged.uniauth_profile,
                        institution=self.inst1, cas_id="user2"),
        ]
        self._check_emails(emails, expected_emails)
        self._check_accounts(accounts, expected_accounts)

        merge_model_instances(self.user3, [self.user4, self.user5])
        self.assertTrue(User.objects.filter(username="user3@gmail.com")\
                .exists())
        self.assertFalse(User.objects.filter(username="us.er4@nowhere.gov")\
                .exists())
        self.assertFalse(User.objects.filter(username="user5@foo.bar")\
                .exists())

        merged = User.objects.get(username="user3@gmail.com")
        emails = list(merged.uniauth_profile.linked_emails.order_by("address"))
        accounts = list(merged.uniauth_profile.accounts.order_by("cas_id"))

        expected_emails = [
                LinkedEmail(profile=merged.uniauth_profile,
                        address="another@gmail.com"),
                LinkedEmail(profile=merged.uniauth_profile,
                        address="backup@gmail.com"),
                LinkedEmail(profile=merged.uniauth_profile,
                        address="huh@what.edu"),
                LinkedEmail(profile=merged.uniauth_profile,
                        address="user3@gmail.com"),
                LinkedEmail(profile=merged.uniauth_profile,
                        address="user5@foo.bar"),
        ]
        expected_accounts = [
                InstitutionAccount(profile=merged.uniauth_profile,
                        institution=self.inst2, cas_id="exid001"),
                InstitutionAccount(profile=merged.uniauth_profile,
                        institution=self.inst1, cas_id="john123"),
        ]
        self._check_emails(emails, expected_emails)
        self._check_accounts(accounts, expected_accounts)

