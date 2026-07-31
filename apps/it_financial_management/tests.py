from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.it_financial_management.services import ITFinancialService
from apps.service_desk.models import Company


class ITFinancialServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="FinCo", slug="fin-co")

    def test_budget_and_chargeback(self):
        year = timezone.localdate().year
        cc = ITFinancialService.ensure_cost_center(self.company, "it-ops", "IT Ops")
        ITFinancialService.set_budget(cc, year, Decimal("100000.00"))
        ITFinancialService.post_chargeback(
            cc, description="Cloud hosting", amount=Decimal("12000.00"), category="cloud"
        )
        status = ITFinancialService.budget_vs_actual(cc, year)
        self.assertEqual(status["spent"], Decimal("12000.00"))
        self.assertEqual(status["remaining"], Decimal("88000.00"))
