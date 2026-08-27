from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.service_desk.models import (
    CABDecision,
    ChangeRequest,
    ChangeTask,
    Department,
    Ticket,
    TicketHistory,
)
from apps.service_desk.selectors.change_management import get_change_requests
from apps.service_desk.services.change_management import (
    approve_change,
    close_change,
    implement_change,
    reject_change,
    schedule_change,
    submit_change,
)
from apps.service_desk.security.policies import get_ticket_queryset


User = get_user_model()


class ChangeManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manager",
            password="password",
        )

        self.user.groups.create(name="Manager")

        self.department = Department.objects.create(
            name="IT",
        )

        self.user.managed_departments.add(self.department)

        self.ticket = Ticket.objects.create(
            title="Change ticket",
            description="Change-related ticket",
            department=self.department,
            created_by=self.user,
        )

        self.change = ChangeRequest.objects.create(
            ticket=self.ticket,
            title="Deploy application release",
            description="Controlled production deployment.",
            risk=ChangeRequest.Risk.MEDIUM,
            requester=self.user,
        )

    def test_change_request_creation_and_ticket_fk(self):
        self.assertEqual(self.change.ticket, self.ticket)
        self.assertEqual(self.change.status, ChangeRequest.Status.DRAFT)

    def test_change_task(self):
        task = ChangeTask.objects.create(
            change=self.change,
            name="Deploy release",
        )

        self.assertEqual(task.change, self.change)
        self.assertFalse(task.completed)

    def test_lifecycle_transitions_and_audit(self):
        submit_change(self.user, self.change)

        self.assertEqual(
            self.change.status,
            ChangeRequest.Status.SUBMITTED,
        )

        approve_change(
            self.user,
            self.change,
            "CAB approved.",
        )

        self.change.refresh_from_db()

        self.assertEqual(
            self.change.status,
            ChangeRequest.Status.APPROVED,
        )

        schedule_change(self.user, self.change)
        implement_change(self.user, self.change)
        close_change(self.user, self.change)

        self.change.refresh_from_db()

        self.assertEqual(
            self.change.status,
            ChangeRequest.Status.CLOSED,
        )

        history = TicketHistory.objects.filter(
            ticket=self.ticket,
            metadata__change_request_id=self.change.pk,
        )

        self.assertGreaterEqual(history.count(), 5)

    def test_cab_approval_decision(self):
        submit_change(self.user, self.change)

        approve_change(
            self.user,
            self.change,
            "Approved for implementation.",
        )

        decision = CABDecision.objects.get(
            change=self.change,
        )

        self.assertEqual(
            decision.decision,
            CABDecision.Decision.APPROVED,
        )
        self.assertEqual(decision.approver, self.user)

    def test_cab_rejection_decision(self):
        submit_change(self.user, self.change)

        reject_change(
            self.user,
            self.change,
            "Risk requires redesign.",
        )

        self.change.refresh_from_db()

        self.assertEqual(
            self.change.status,
            ChangeRequest.Status.REJECTED,
        )

        decision = CABDecision.objects.get(
            change=self.change,
        )

        self.assertEqual(
            decision.decision,
            CABDecision.Decision.REJECTED,
        )

    def test_rbac_visibility_uses_ticket_queryset_pattern(self):
        visible_tickets = get_ticket_queryset(self.user)
        visible_changes = get_change_requests(self.user)

        self.assertIn(self.ticket, visible_tickets)
        self.assertIn(self.change, visible_changes)

    def test_audit_record_is_created(self):
        submit_change(self.user, self.change)

        record = TicketHistory.objects.filter(
            ticket=self.ticket,
            event_type=TicketHistory.EVENT_UPDATED,
            old_value=ChangeRequest.Status.DRAFT,
            new_value=ChangeRequest.Status.SUBMITTED,
        ).first()

        self.assertIsNotNone(record)
        self.assertEqual(record.performed_by, self.user)