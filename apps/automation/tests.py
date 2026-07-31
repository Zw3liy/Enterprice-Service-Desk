from django.test import TestCase
from apps.automation.services import AutomationService
class AutoTests(TestCase):
    def test_import(self):
        self.assertTrue(hasattr(AutomationService, "dispatch"))
