from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.business_rules.services import BusinessRulesEngine
from apps.service_desk.models import Company, Department, Status
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class BusinessRulesTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="RuleCo", slug="rule-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(
            username="ruleuser", password="pass12345", is_staff=True
        )

    def test_evaluate_adds_tag(self):
        ticket = TicketService.create_ticket(
            title="VIP outage",
            company=self.company,
            actor=self.user,
            run_ai=False,
        )
        BusinessRulesEngine.create_rule(
            self.company,
            name="Tag VIP",
            scope="ticket",
            conditions={},
            actions=[{"type": "add_tag", "tag": "vip-rule"}],
            priority=1,
        )
        applied = BusinessRulesEngine.evaluate(
            self.company,
            "ticket",
            {"ticket": ticket, "ticket_type": ticket.ticket_type, "tags": ticket.tags or []},
        )
        self.assertEqual(applied, ["Tag VIP"])
        ticket.refresh_from_db()
        self.assertIn("vip-rule", ticket.tags or [])
