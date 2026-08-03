from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.executive_dashboard.services import ExecutiveDashboardService
from apps.service_desk.models import Company

User = get_user_model()


class ExecutiveDashboardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="ExecCo", slug="exec-co")
        self.user = User.objects.create_user(
            username="exec", password="pass12345", is_staff=True
        )
        self.client = Client()
        self.client.login(username="exec", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_board_pack_and_ui(self):
        pack = ExecutiveDashboardService.board_pack(company=self.company, user=self.user)
        self.assertIn("kpis", pack)
        self.assertIn("portfolio", pack)
        res = self.client.get(reverse("executive:home"))
        self.assertEqual(res.status_code, 200)
