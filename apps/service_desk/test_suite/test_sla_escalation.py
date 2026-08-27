from django.test import TestCase
from django.utils.timezone import now, timedelta
from apps.service_desk.models.ticket import Ticket
from django.contrib.auth.models import User
from apps.service_desk.models.sla_policy import SLAPolicy
from apps.service_desk.sla.escalation import SLAEscalationService, SLAEscalation
from apps.service_desk.services.sla_service import SLAService

class SLAEscalationTests(TestCase):

    def setUp(self):
        self.policy = SLAPolicy.objects.create(name="Fast SLA", duration_minutes=1)
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.ticket = Ticket.objects.create(created_by=self.user, sla_policy=self.policy)

    def test_sla_breach_creates_escalation(self):
        # Move ticket create time to past to breach SLA
        self.ticket.created_at = now() - timedelta(minutes=5)
        self.ticket.save()

        result = SLAEscalationService.escalate_breach(self.ticket)

        self.assertTrue(result)
        self.assertEqual(SLAEscalation.objects.filter(ticket=self.ticket).count(), 1)

    def test_no_duplicate_escalation_on_same_breach(self):
        self.ticket.created_at = now() - timedelta(minutes=5)
        self.ticket.save()

        first_call = SLAEscalationService.escalate_breach(self.ticket)
        second_call = SLAEscalationService.escalate_breach(self.ticket)

        self.assertTrue(first_call)
        self.assertFalse(second_call)  # second call should not create another escalation
        self.assertEqual(SLAEscalation.objects.filter(ticket=self.ticket).count(), 1)

    def test_no_escalation_if_no_breach(self):
        self.ticket.created_at = now() + timedelta(minutes=10)  # future created_at
        self.ticket.save()

        result = SLAEscalationService.escalate_breach(self.ticket)

        self.assertFalse(result)

    def test_notification_sent_to_authorized_user(self):
        self.ticket.created_at = now() - timedelta(minutes=5)
        self.ticket.assigned_to = self.user
        self.ticket.save()

        # patch the notify method to capture calls
        self.notifications = []
        def fake_notify(user, message):
            self.notifications.append((user.username, message))

        original_notify = SLAEscalationService.escalate_breach.__globals__['notify']
        SLAEscalationService.escalate_breach.__globals__['notify'] = fake_notify

        SLAEscalationService.escalate_breach(self.ticket)

        # restore original notify
        SLAEscalationService.escalate_breach.__globals__['notify'] = original_notify

        self.assertTrue(len(self.notifications) > 0)
        self.assertIn(self.user.username, [n[0] for n in self.notifications])

    def test_rbac_restriction_on_notification(self):
        # Only users with ticket visibility receive notification
        # Create unauthorized user
        unauthorized_user = User.objects.create_user(username="unauth", password="pass")
        self.ticket.created_at = now() - timedelta(minutes=5)
        self.ticket.assigned_to = self.user
        self.ticket.save()

        # Patch notify and check only authorized notified
        notified_users = []

        def fake_notify(user, message):
            notified_users.append(user.username)

        original_notify = SLAEscalationService.escalate_breach.__globals__['notify']
        SLAEscalationService.escalate_breach.__globals__['notify'] = fake_notify

        SLAEscalationService.escalate_breach(self.ticket)

        SLAEscalationService.escalate_breach.__globals__['notify'] = original_notify

        self.assertIn(self.user.username, notified_users)
        self.assertNotIn(unauthorized_user.username, notified_users)
