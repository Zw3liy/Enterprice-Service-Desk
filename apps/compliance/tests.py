from django.test import TestCase

from apps.compliance.models import Control
from apps.compliance.services import ComplianceService
from apps.service_desk.models import Company


class ComplianceServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="CompCo", slug="comp-co")

    def test_iso_bootstrap_scorecard(self):
        fw = ComplianceService.ensure_iso27001(self.company)
        self.assertGreaterEqual(fw.controls.count(), 5)
        control = fw.controls.first()
        ComplianceService.set_status(control, Control.Status.COMPLIANT)
        score = ComplianceService.scorecard(fw)
        self.assertIn("compliance_pct", score)
        self.assertGreaterEqual(score["compliance_pct"], 0)
