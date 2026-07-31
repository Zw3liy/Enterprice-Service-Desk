from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics_engine.services import KPIEngine, MetricsEngine
from apps.service_desk.models import Company

User = get_user_model()


class AnalyticsEngineTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="AnCo", slug="an-co")
        self.user = User.objects.create_user(username="anuser", password="pass12345")

    def test_kpi_and_snapshot(self):
        kpis = KPIEngine.compute(company=self.company, user=self.user)
        self.assertIn("open_tickets", kpis)
        snap = MetricsEngine.capture_snapshot(self.company)
        self.assertEqual(snap.company_id, self.company.pk)
        self.assertTrue(MetricsEngine.latest(self.company))
