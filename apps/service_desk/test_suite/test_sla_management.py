from django.test import TestCase
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError
from apps.service_desk.models.sla_policy import SLAPolicy
from apps.service_desk.models.ticket import Ticket
from apps.service_desk.services.sla_service import SLAService
from apps.service_desk.selectors.sla_selector import SLASelector
from django.contrib.auth import get_user_model

User = get_user_model()

class SLAPolicyModelTests(TestCase):

    def test_duration_returns_timedelta(self):
        policy = SLAPolicy(name="Test Policy", duration_minutes=15)
        self.assertIsInstance(policy.duration(), timedelta)

    def test_clean_raises_for_non_positive_duration(self):
        policy = SLAPolicy(name="Invalid Policy", duration_minutes=0)
        with self.assertRaises(ValidationError):
            policy.clean()

    def test_str_representation(self):
        policy = SLAPolicy(name="My Policy", duration_minutes=30)
        self.assertEqual(str(policy), "My Policy")

class SLAServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="password")
        self.policy = SLAPolicy.objects.create(name="Standard SLA", duration_minutes=60)

    def test_calculate_sla_deadline_returns_none_if_no_policy(self):
        ticket = Ticket(created_at=now())
        ticket.sla_policy = None
        deadline = SLAService.calculate_sla_deadline(ticket)
        self.assertIsNone(deadline)

    def test_calculate_sla_deadline_returns_correct_deadline(self):
        ticket = Ticket(created_at=now())
        ticket.sla_policy = self.policy
        expected_deadline = ticket.created_at + self.policy.duration()
        self.assertEqual(SLAService.calculate_sla_deadline(ticket), expected_deadline)

    def test_check_sla_breach_false_if_no_policy(self):
        ticket = Ticket(created_at=now())
        ticket.sla_policy = None
        self.assertFalse(SLAService.check_sla_breach(ticket))

    def test_check_sla_breach_true_and_false(self):
        past_time = now() - timedelta(hours=2)
        future_time = now() + timedelta(hours=2)
        ticket = Ticket(created_at=past_time)
        ticket.sla_policy = self.policy
        self.assertTrue(SLAService.check_sla_breach(ticket))
        ticket.created_at = future_time
        self.assertFalse(SLAService.check_sla_breach(ticket))

class SLASelectorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="admin123")
        self.policy = SLAPolicy.objects.create(name="Quick SLA", duration_minutes=1)

    def test_get_tickets_breached_sla_returns_tickets(self):
        ticket1 = Ticket.objects.create(created_at=now() - timedelta(minutes=10), sla_policy=self.policy)
        ticket2 = Ticket.objects.create(created_at=now() + timedelta(minutes=10), sla_policy=self.policy)

        breached_tickets = SLASelector.get_tickets_breached_sla(self.admin)

        self.assertTrue(breached_tickets.filter(pk=ticket1.pk).exists())
        self.assertFalse(breached_tickets.filter(pk=ticket2.pk).exists())
