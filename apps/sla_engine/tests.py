from django.test import TestCase
from apps.sla_engine.services import SLAService
from apps.service_desk.models import Company
class SLAEngineImportTests(TestCase):
    def test_import(self):
        self.assertTrue(callable(SLAService.scan_open_tickets))
