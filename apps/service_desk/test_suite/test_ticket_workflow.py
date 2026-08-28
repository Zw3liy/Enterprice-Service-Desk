"""
IM-03

Regression coverage for the Incident Lifecycle Completion milestone:

- TicketService is now wired into real views (assign, status change,
  comment, close, reopen, create) rather than sitting unused.
- Ticket detail page renders actual TicketHistory instead of a
  hardcoded "No updates yet" stub.
- Reassignment now captures the previous assignee in history
  (assign_ticket previously only recorded new_value).
- Every workflow action is scoped through get_ticket_queryset(user),
  not a raw pk lookup, so RBAC is preserved.

Note: get_ticket_queryset scopes Technician visibility to tickets
*already assigned to them* (security/policies.py — "Technician:
assigned tickets", by design, confirmed pre-existing). An unassigned
ticket is invisible to a Technician under current policy, so initial
assignment in these tests is performed by a Manager (department-
scoped, sees unassigned department tickets), matching real RBAC
behavior rather than assuming a Technician can self-serve arbitrary
unassigned tickets.
"""

from django.test import TestCase, Client

from django.contrib.auth.models import User, Group, Permission

from apps.service_desk.models import Department, Ticket, TicketHistory
from apps.service_desk.services.ticket_service import TicketService


class TicketWorkflowViewTests(TestCase):

    def setUp(self):

        self.client = Client()

        technician_group = Group.objects.create(name="Technician")
        manager_group = Group.objects.create(name="Manager")
        requester_group = Group.objects.create(name="Requester")

        view_ticket = Permission.objects.get(codename="view_ticket")
        change_ticket = Permission.objects.get(codename="change_ticket")

        technician_group.permissions.add(view_ticket, change_ticket)
        manager_group.permissions.add(view_ticket, change_ticket)
        requester_group.permissions.add(view_ticket)

        self.technician = User.objects.create_user(
            username="im03_technician",
            password="password123",
        )
        self.technician.groups.add(technician_group)

        self.other_technician = User.objects.create_user(
            username="im03_technician2",
            password="password123",
        )
        self.other_technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="im03_manager",
            password="password123",
        )
        self.manager.groups.add(manager_group)

        self.requester = User.objects.create_user(
            username="im03_requester",
            password="password123",
        )
        self.requester.groups.add(requester_group)

        self.department = Department.objects.create(
            name="IM-03 Department",
        )

        self.department.managers.add(self.manager)

        self.ticket = Ticket.objects.create(
            title="Workflow test ticket",
            description="Testing IM-03 workflow views",
            status="open",
            created_by=self.requester,
            department=self.department,
        )

    # --------------------------------------------------
    # Assignment (performed by a Manager — see module docstring)
    # --------------------------------------------------

    def test_manager_can_assign_unassigned_ticket(self):

        self.client.login(
            username="im03_manager",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/assign/",
            {"technician_id": self.technician.pk},
        )

        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.assigned_to, self.technician)

    def test_reassignment_captures_previous_assignee_in_history(self):

        TicketService.assign_ticket(
            self.ticket,
            self.technician,
            user=self.manager,
        )

        TicketService.assign_ticket(
            self.ticket,
            self.other_technician,
            user=self.manager,
        )

        latest = self.ticket.history.filter(
            event_type=TicketHistory.EVENT_ASSIGNED
        ).order_by("-created_at").first()

        self.assertEqual(latest.old_value, "im03_technician")
        self.assertEqual(latest.new_value, "im03_technician2")

    def test_requester_cannot_assign_ticket(self):

        self.client.login(
            username="im03_requester",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/assign/",
            {"technician_id": self.technician.pk},
        )

        self.assertEqual(response.status_code, 403)

    def test_technician_can_see_unassigned_ticket(self):

        # ADR-010, Decision 2: Technicians can see unassigned
        # tickets (queue-based self-assignment), not just tickets
        # already assigned to them.
        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.get(f"/tickets/{self.ticket.pk}/")

        self.assertEqual(response.status_code, 200)

    def test_technician_can_self_assign_unassigned_ticket(self):

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/assign/",
            {"technician_id": self.technician.pk},
        )

        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.assigned_to, self.technician)

    # --------------------------------------------------
    # Status change (technician acting on a ticket assigned to them)
    # --------------------------------------------------

    def test_valid_status_transition_succeeds(self):

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/status/",
            {"status": "in_progress"},
        )

        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "in_progress")

    def test_invalid_status_transition_is_rejected(self):

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/status/",
            {"status": "closed"},
        )

        self.ticket.refresh_from_db()

        # open -> closed is not a valid transition; ticket must be
        # unchanged and the request should redirect back (not 500).
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "open")

    # --------------------------------------------------
    # Comments
    # --------------------------------------------------

    def test_requester_can_comment_on_own_ticket(self):

        self.client.login(
            username="im03_requester",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/comment/",
            {"comment": "Any update on this?"},
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            self.ticket.history.filter(
                event_type=TicketHistory.EVENT_COMMENT,
                comment="Any update on this?",
            ).exists()
        )

    def test_detail_page_renders_history_entries(self):

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )

        TicketService.add_comment(
            self.ticket,
            "Investigating the issue.",
            user=self.technician,
        )

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.get(f"/tickets/{self.ticket.pk}/")

        self.assertContains(response, "Investigating the issue.")

    # --------------------------------------------------
    # Close / Reopen
    # --------------------------------------------------

    def test_cannot_close_ticket_that_is_not_awaiting_confirmation(self):
        """
        IM-04: close_ticket now requires awaiting_confirmation status,
        not resolved (ADR-010, Decision 3).
        """

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/close/",
        )

        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "open")

    def test_requester_confirmation_close_then_reopen_cycle(self):
        """
        IM-04: full resolved → awaiting_confirmation → closed →
        reopened cycle, with requester confirmation enforced
        (ADR-010, Decision 3).
        """

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )
        TicketService.change_status(
            self.ticket, "in_progress", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "resolved", user=self.technician
        )

        # Technician sends for requester confirmation
        self.client.login(
            username="im03_technician",
            password="password123",
        )

        confirm_response = self.client.post(
            f"/tickets/{self.ticket.pk}/request-confirmation/",
        )

        self.ticket.refresh_from_db()

        self.assertEqual(confirm_response.status_code, 302)
        self.assertEqual(self.ticket.status, "awaiting_confirmation")

        # Only the requester can close from awaiting_confirmation
        self.client.login(
            username="im03_requester",
            password="password123",
        )

        close_response = self.client.post(
            f"/tickets/{self.ticket.pk}/close/",
        )

        self.ticket.refresh_from_db()

        self.assertEqual(close_response.status_code, 302)
        self.assertEqual(self.ticket.status, "closed")

        # Reopen (anyone with change_ticket)
        self.client.login(
            username="im03_technician",
            password="password123",
        )

        reopen_response = self.client.post(
            f"/tickets/{self.ticket.pk}/reopen/",
        )

        self.ticket.refresh_from_db()

        self.assertEqual(reopen_response.status_code, 302)
        self.assertEqual(self.ticket.status, "open")

    def test_non_requester_cannot_close_awaiting_confirmation_ticket(self):
        """
        IM-04: a Technician cannot close a ticket in
        awaiting_confirmation — only the requester can
        (ADR-010, Decision 3).
        """

        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.manager
        )
        TicketService.change_status(
            self.ticket, "in_progress", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "resolved", user=self.technician
        )
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician
        )

        self.client.login(
            username="im03_technician",
            password="password123",
        )

        response = self.client.post(
            f"/tickets/{self.ticket.pk}/close/",
        )

        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "awaiting_confirmation")

    # --------------------------------------------------
    # Ticket creation now routed through TicketService
    # --------------------------------------------------

    def test_ticket_creation_still_works_through_service_layer(self):

        add_ticket = Permission.objects.get(codename="add_ticket")
        self.requester.user_permissions.add(add_ticket)

        from apps.service_desk.models import RequestType

        request_type = RequestType.objects.create(
            name="IM-03 Service Request",
            is_active=True,
        )

        self.client.login(
            username="im03_requester",
            password="password123",
        )

        response = self.client.post(
            "/tickets/new/",
            {
                "title": "New service-layer ticket",
                "description": "Created via TicketService.create_ticket",
                "priority": "medium",
                "urgency": "medium",
                "request_type": str(request_type.pk),
                "department": str(self.department.pk),
                "tags": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        ticket = Ticket.objects.get(title="New service-layer ticket")

        self.assertEqual(ticket.created_by, self.requester)
        self.assertEqual(ticket.request_type, request_type)

        self.assertTrue(
            ticket.history.filter(
                event_type=TicketHistory.EVENT_CREATED
            ).exists()
        )
