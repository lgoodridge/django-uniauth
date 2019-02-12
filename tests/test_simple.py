"""
Tests that the testing framework itself is working correctly.
"""

from django.test import TestCase
from uniauth.models import UserProfile

class SimpleTestCase(TestCase):

    def setUp(self):
        pass

    def test_simple(self):
        self.assertTrue(True, "True is not True?!")
        self.assertFalse(False, "False is not False?!")
