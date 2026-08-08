from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.utils.timezone import now, timedelta
from apps.service_desk.models import Ticket, Department, SLAPolicy
from apps.service_desk.services.sla_service import SLAService


class SLAManagementTests(TestCase):

    def setUp(self):
        self.group = Group.objects.create(name="Technician")
        view_perm = Permission.objects.get(codename="view_ticket")
        change_perm = Permission.objects.get(codename="change_ticket")
        self.group.permissions.add(view_perm, change_perm)

        self.user = User.objects.create_user(username="technician", password="password123")
        self.user.groups.add(self.group)

        self.department = Department.objects.create(name="SLA Dept")

        self.sla_policy = SLAPolicy.objects.create(name="Standard 2 hours", duration_minutes=120)

        self.ticket = Ticket.objects.create(
            title="Ticket with SLA",
            description="Some issue",
            priority="medium",
            urgency="medium",
            status="open",
            created_by=self.user,
            department=self.department,
            sla_policy=self.sla_policy,
        )

    def test_sla_deadline_calculation(self):
        deadline = SLAService.calculate_sla_deadline(self.ticket)
        self.assertIsNotNone(deadline)
        expected = self.ticket.created_at + self.sla_policy.duration()
        self.assertEqual(deadline, expected)

    def test_sla_breach_detection_false(self):
        self.assertFalse(SLAService.check_sla_breach(self.ticket))

    def test_sla_breach_detection_true(self):
        # Artificially set created_at to past to cause breach
        self.ticket.created_at = now() - timedelta(minutes=180)
        self.ticket.save(update_fields=['created_at'])
        self.assertTrue(SLAService.check_sla_breach(self.ticket))

    def test_invalid_sla_policy_configuration(self):
        with self.assertRaises(Exception):
            SLAPolicy.objects.create(name="Invalid SLA", duration_minutes=0)

    def test_rbac_ticket_visibility(self):
        from apps.service_desk.security.policies import get_ticket_queryset
        tickets_visible = get_ticket_queryset(self.user)
        self.assertIn(self.ticket, tickets_visible)

    def test_timezone_aware_deadline(self):
        deadline = SLAService.calculate_sla_deadline(self.ticket)
        self.assertTrue(deadline.tzinfo is not None and deadline.tzinfo.utcoffset(deadline) is not None)

    def test_ticket_without_sla_policy(self):
        ticket_no_sla = Ticket.objects.create(
            title="No SLA Ticket",
            description="No SLA set",
            priority="low",
            urgency="low",
            status="open",
            created_by=self.user,
            department=self.department,
        )
        deadline = SLAService.calculate_sla_deadline(ticket_no_sla)
        self.assertIsNone(deadline)
        self.assertFalse(SLAService.check_sla_breach(ticket_no_sla))
