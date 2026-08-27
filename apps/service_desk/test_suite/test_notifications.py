"""
NOTIFY-01 — internal notification boundary.

Covers the in-app record (always written), the optional email mirror
(off by default, never fatal), the ticket/SLA/problem call sites, and
the ownership boundary on reading.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.service_desk.models import (
    Department,
    Notification,
    Problem,
    SLAPolicy,
    Ticket,
    TicketSLA,
)
from apps.service_desk.selectors.notification_selector import (
    NotificationSelector,
)
from apps.service_desk.services.notification_service import (
    NotificationService,
)
from apps.service_desk.services.sla_service import SLAService
from apps.service_desk.services.ticket_service import TicketService


class NotificationDeliveryTests(TestCase):

    def setUp(self):
        self.it = Department.objects.create(name="IT")

        self.requester = User.objects.create_user(
            username="notify-requester",
            password="password123",
            email="requester@example.com",
        )

        self.technician = User.objects.create_user(
            username="notify-technician",
            password="password123",
            email="tech@example.com",
        )

        self.ticket = Ticket.objects.create(
            title="Printer down",
            description="d",
            department=self.it,
            created_by=self.requester,
        )

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------

    def test_notification_is_persisted_in_app(self):
        notification = NotificationService.notify(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_ASSIGNED,
            subject="Assigned",
            ticket=self.ticket,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.technician)
        self.assertFalse(notification.is_read)

    def test_actor_is_never_notified_about_their_own_action(self):
        result = NotificationService.notify(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_STATUS,
            subject="Own action",
            actor=self.technician,
        )

        self.assertIsNone(result)
        self.assertEqual(Notification.objects.count(), 0)

    def test_inactive_recipients_are_skipped(self):
        self.technician.is_active = False
        self.technician.save()

        self.assertIsNone(
            NotificationService.notify(
                recipient=self.technician,
                kind=Notification.KIND_TICKET_STATUS,
                subject="Nope",
            )
        )

    def test_no_email_is_sent_when_notifications_are_disabled(self):
        NotificationService.notify(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_ASSIGNED,
            subject="No email please",
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(Notification.objects.first().emailed)

    @override_settings(SERVICE_DESK_EMAIL_NOTIFICATIONS=True)
    def test_email_mirror_is_sent_when_enabled(self):
        NotificationService.notify(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_ASSIGNED,
            subject="Emailed",
            body="Body",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["tech@example.com"])
        self.assertTrue(Notification.objects.first().emailed)

    @override_settings(SERVICE_DESK_EMAIL_NOTIFICATIONS=True)
    def test_recipient_without_an_address_is_still_notified_in_app(self):
        self.technician.email = ""
        self.technician.save()

        notification = NotificationService.notify(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_ASSIGNED,
            subject="No address",
        )

        self.assertIsNotNone(notification)
        self.assertFalse(notification.emailed)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        SERVICE_DESK_EMAIL_NOTIFICATIONS=True,
        EMAIL_BACKEND="apps.service_desk.test_suite.test_notifications."
        "ExplodingEmailBackend",
    )
    def test_a_broken_mail_backend_never_breaks_the_operation(self):
        """
        The single most important property of this boundary.
        """

        with self.assertLogs(
            "apps.service_desk.services.notification_service",
            level="ERROR",
        ):
            notification = NotificationService.notify(
                recipient=self.technician,
                kind=Notification.KIND_TICKET_ASSIGNED,
                subject="Backend is down",
            )

        self.assertIsNotNone(notification)
        self.assertFalse(notification.emailed)

    # ------------------------------------------------------------------
    # Ticket call sites
    # ------------------------------------------------------------------

    def test_assignment_notifies_the_new_assignee(self):
        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.requester
        )

        notification = Notification.objects.get(
            recipient=self.technician,
            kind=Notification.KIND_TICKET_ASSIGNED,
        )
        self.assertEqual(notification.ticket, self.ticket)

    def test_status_change_notifies_requester_and_assignee(self):
        self.ticket.assigned_to = self.technician
        self.ticket.save()

        manager = User.objects.create_user(
            username="notify-manager", password="password123"
        )

        TicketService.change_status(self.ticket, "in_progress", user=manager)

        recipients = set(
            Notification.objects.filter(
                kind=Notification.KIND_TICKET_STATUS
            ).values_list("recipient__username", flat=True)
        )

        self.assertEqual(
            recipients, {"notify-requester", "notify-technician"}
        )

    def test_awaiting_confirmation_notifies_only_the_requester(self):
        self.ticket.assigned_to = self.technician
        self.ticket.save()

        TicketService.change_status(
            self.ticket, "in_progress", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "resolved", user=self.technician
        )
        Notification.objects.all().delete()

        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician
        )

        notifications = Notification.objects.filter(
            kind=Notification.KIND_CONFIRMATION_REQUESTED
        )

        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().recipient, self.requester)

    def test_requester_confirmation_notifies_the_assignee(self):
        self.ticket.assigned_to = self.technician
        self.ticket.save()

        TicketService.change_status(
            self.ticket, "in_progress", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "resolved", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician
        )
        Notification.objects.all().delete()

        TicketService.change_status(
            self.ticket, "closed", user=self.requester
        )

        notification = Notification.objects.get(
            kind=Notification.KIND_TICKET_CONFIRMED
        )
        self.assertEqual(notification.recipient, self.technician)

    def test_notification_body_never_carries_work_note_content(self):
        self.ticket.assigned_to = self.technician
        self.ticket.save()

        TicketService.add_work_note(
            self.ticket,
            "Internal: the customer is being difficult",
            user=self.technician,
        )

        for notification in Notification.objects.all():
            self.assertNotIn("difficult", notification.body)

    # ------------------------------------------------------------------
    # SLA call site
    # ------------------------------------------------------------------

    def test_sla_breach_notifies_the_assignee(self):
        SLAPolicy.objects.create(
            name="Global Medium",
            priority="medium",
            response_minutes=15,
            resolution_minutes=60,
        )

        self.ticket.assigned_to = self.technician
        self.ticket.save()

        record = SLAService.attach_to_ticket(self.ticket)
        Notification.objects.all().delete()

        SLAService.evaluate(record, now=timezone.now() + timedelta(hours=3))

        kinds = set(
            Notification.objects.filter(
                recipient=self.technician
            ).values_list("kind", flat=True)
        )
        self.assertIn(Notification.KIND_SLA_BREACH, kinds)

    def test_unassigned_sla_breach_falls_back_to_department_managers(self):
        SLAPolicy.objects.create(
            name="Global Medium",
            priority="medium",
            response_minutes=15,
            resolution_minutes=60,
        )

        manager = User.objects.create_user(
            username="dept-manager", password="password123"
        )
        self.it.managers.add(manager)

        record = SLAService.attach_to_ticket(self.ticket)
        Notification.objects.all().delete()

        SLAService.evaluate(record, now=timezone.now() + timedelta(hours=3))

        self.assertTrue(
            Notification.objects.filter(recipient=manager).exists()
        )

    # ------------------------------------------------------------------
    # Problem call site
    # ------------------------------------------------------------------

    def test_problem_notifications_skip_users_without_problem_access(self):
        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.set(
            Permission.objects.filter(codename="view_problem")
        )
        self.technician.groups.add(technician_group)

        problem = Problem.objects.create(
            title="Recurring outage",
            description="d",
            department=self.it,
            assigned_to=self.technician,
            created_by=self.requester,  # no view_problem permission
        )

        NotificationService.notify_problem_update(
            problem, "Root cause recorded", "detail"
        )

        recipients = set(
            Notification.objects.filter(
                kind=Notification.KIND_PROBLEM_UPDATE
            ).values_list("recipient__username", flat=True)
        )

        self.assertEqual(recipients, {"notify-technician"})


class NotificationAccessTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.alice = User.objects.create_user(
            username="alice", password="password123"
        )
        self.bob = User.objects.create_user(
            username="bob", password="password123"
        )

        self.alice_notification = Notification.objects.create(
            recipient=self.alice,
            kind=Notification.KIND_TICKET_STATUS,
            subject="Alice only",
        )
        self.bob_notification = Notification.objects.create(
            recipient=self.bob,
            kind=Notification.KIND_TICKET_STATUS,
            subject="Bob only",
        )

    def test_selector_returns_only_the_users_own_notifications(self):
        self.assertEqual(
            list(NotificationSelector.for_user(self.alice)),
            [self.alice_notification],
        )
        self.assertEqual(NotificationSelector.unread_count(self.alice), 1)

    def test_anonymous_selector_returns_nothing(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(
            NotificationSelector.for_user(AnonymousUser()).count(), 0
        )

    def test_anonymous_inbox_redirects_to_login(self):
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_inbox_shows_only_own_notifications(self):
        self.client.login(username="alice", password="password123")
        response = self.client.get("/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice only")
        self.assertNotContains(response, "Bob only")

    def test_cannot_read_another_users_notification(self):
        self.client.login(username="alice", password="password123")

        response = self.client.post(
            f"/notifications/{self.bob_notification.pk}/read/"
        )

        self.assertEqual(response.status_code, 404)
        self.bob_notification.refresh_from_db()
        self.assertIsNone(self.bob_notification.read_at)

    def test_service_layer_refuses_a_foreign_read(self):
        with self.assertRaises(PermissionError):
            NotificationService.mark_read(
                self.bob_notification, self.alice
            )

    def test_marking_read_and_mark_all_read(self):
        self.client.login(username="alice", password="password123")

        self.client.post(
            f"/notifications/{self.alice_notification.pk}/read/"
        )
        self.alice_notification.refresh_from_db()
        self.assertTrue(self.alice_notification.is_read)

        Notification.objects.create(
            recipient=self.alice,
            kind=Notification.KIND_TICKET_STATUS,
            subject="Another",
        )

        self.client.post("/notifications/read-all/")
        self.assertEqual(NotificationSelector.unread_count(self.alice), 0)

    def test_navigation_context_processor_exposes_unread_count(self):
        self.client.login(username="alice", password="password123")
        response = self.client.get("/notifications/")

        self.assertEqual(response.context["nav_unread_notifications"], 1)


class ExplodingEmailBackend:
    """
    Email backend that fails the way a misconfigured SMTP server does.
    """

    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise OSError("SMTP server unreachable")

    def open(self):
        raise OSError("SMTP server unreachable")

    def close(self):
        pass
