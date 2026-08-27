from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.service_desk.models import (
    ChangeRequest,
    Department,
    Release,
    ReleaseItem,
    Ticket,
    TicketHistory,
)
from apps.service_desk.security.policies import (
    get_ticket_queryset,
    is_manager,
)
from apps.service_desk.services.release_management import (
    execute_deployment,
    rollback_release,
    schedule_release,
)


User = get_user_model()


class ReleaseManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="release_manager",
            password="password",
        )
        self.department = Department.objects.create(
            name="Release Management",
        )
        self.user.groups.create(name="Manager")
        self.user.managed_departments.add(self.department)

        self.ticket = Ticket.objects.create(
            title="Approved change",
            description="Release test ticket",
            department=self.department,
            created_by=self.user,
        )

        self.change = ChangeRequest.objects.create(
            ticket=self.ticket,
            title="Approved production change",
            description="Release deployment",
            risk="low",
            planned_start=timezone.now(),
            planned_end=timezone.now() + timedelta(hours=2),
            status="approved",
            requester=self.user,
        )

        self.release = Release.objects.create(
            change_request=self.change,
            version_number="2026.08.1",
            scheduled_deployment_time=timezone.now() + timedelta(hours=1),
            release_notes="Initial release",
        )

    def test_release_creation_and_change_request_fk(self):
        item = ReleaseItem.objects.create(
            release=self.release,
            name="Ticketing application",
            component="service_desk",
            artifact="release-2026.08.1",
        )

        self.assertEqual(self.release.change_request, self.change)
        self.assertEqual(item.release, self.release)
        self.assertFalse(item.deployed)

    def test_manager_has_release_visibility_through_ticket_queryset(self):
        self.assertTrue(is_manager(self.user))
        visible_tickets = get_ticket_queryset(self.user)

        self.assertIn(self.ticket, visible_tickets)

    def test_schedule_release_records_audit_event(self):
        schedule_release(
            release=self.release,
            user=self.user,
        )

        self.release.refresh_from_db()

        self.assertEqual(
            self.release.status,
            Release.Status.PLANNED,
        )
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=self.ticket,
                event_type=TicketHistory.EVENT_UPDATED,
                performed_by=self.user,
                metadata__release_id=self.release.pk,
            ).exists()
        )

    def test_execute_deployment_records_audit_event(self):
        execute_deployment(
            release=self.release,
            user=self.user,
        )

        self.release.refresh_from_db()

        self.assertEqual(
            self.release.status,
            Release.Status.IN_PROGRESS,
        )
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=self.ticket,
                event_type=TicketHistory.EVENT_UPDATED,
                performed_by=self.user,
                metadata__action="execute_deployment",
            ).exists()
        )

    def test_rollback_release_records_audit_event(self):
        execute_deployment(
            release=self.release,
            user=self.user,
        )

        rollback_release(
            release=self.release,
            user=self.user,
        )

        self.release.refresh_from_db()

        self.assertEqual(
            self.release.status,
            Release.Status.ROLLED_BACK,
        )
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=self.ticket,
                event_type=TicketHistory.EVENT_UPDATED,
                performed_by=self.user,
                metadata__action="rollback_release",
            ).exists()
        )

    def test_unauthorized_user_cannot_manage_release(self):
        other_user = User.objects.create_user(
            username="unauthorized",
            password="password",
        )

        with self.assertRaises(PermissionError):
            execute_deployment(
                release=self.release,
                user=other_user,
            )