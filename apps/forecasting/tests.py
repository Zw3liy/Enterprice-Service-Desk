from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.forecasting.services import ForecastingService
from apps.service_desk.models import Company, Department, Status
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class ForecastingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="FcCo", slug="fc-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(username="fcuser", password="pass12345")
        for i in range(5):
            TicketService.create_ticket(
                title=f"t{i}",
                company=self.company,
                actor=self.user,
                run_ai=False,
            )

    def test_forecast_shape(self):
        data = ForecastingService.ticket_volume_forecast(
            self.company, history_days=14, horizon_days=5
        )
        self.assertEqual(len(data["forecast"]), 5)
        self.assertIn("baseline", data)
        staff = ForecastingService.staffing_suggestion(self.company)
        self.assertGreaterEqual(staff["suggested_agents"], 1)
