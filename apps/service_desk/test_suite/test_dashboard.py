"""
Regression coverage for the main enterprise dashboard.

The dashboard must derive every number it renders from the
RBAC-scoped queryset (``get_ticket_queryset``), never from
``Ticket.objects``. These tests pin that behaviour per role so a
future refactor cannot silently leak cross-user or cross-department
data into the dashboard cards.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import Department, Problem, Ticket


class DashboardScopingTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        view_ticket = Permission.objects.get(codename="view_ticket")
        add_ticket = Permission.objects.get(codename="add_ticket")
        change_ticket = Permission.objects.get(codename="change_ticket")
        view_problem = Permission.objects.get(codename="view_problem")

        requester_group = Group.objects.create(name="Requester")
        requester_group.permissions.set([view_ticket, add_ticket])

        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.set(
            [view_ticket, change_ticket, view_problem]
        )

        manager_group = Group.objects.create(name="Manager")
        manager_group.permissions.set(
            [view_ticket, change_ticket, view_problem]
        )

        self.requester = User.objects.create_user(
            username="requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.other_requester = User.objects.create_user(
            username="other-requester", password="password123"
        )
        self.other_requester.groups.add(requester_group)

        self.technician = User.objects.create_user(
            username="technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.it.managers.add(self.manager)

        self.admin = User.objects.create_superuser(
            username="admin",
            password="password123",
            email="admin@example.com",
        )

        # Requester's own tickets: 1 open, 1 resolved.
        self.own_open = Ticket.objects.create(
            title="Own open",
            description="d",
            status="open",
            department=self.it,
            created_by=self.requester,
        )
        self.own_resolved = Ticket.objects.create(
            title="Own resolved",
            description="d",
            status="resolved",
            department=self.it,
            created_by=self.requester,
        )

        # Another requester's ticket — must never appear.
        self.foreign_ticket = Ticket.objects.create(
            title="Foreign ticket",
            description="d",
            status="open",
            department=self.hr,
            created_by=self.other_requester,
        )

        # HR ticket assigned to somebody — outside the manager's scope.
        self.hr_assigned = Ticket.objects.create(
            title="HR assigned",
            description="d",
            status="in_progress",
            department=self.hr,
            created_by=self.other_requester,
            assigned_to=self.admin,
        )

        # IT ticket assigned to the technician.
        self.tech_ticket = Ticket.objects.create(
            title="Tech assigned",
            description="d",
            status="in_progress",
            priority="urgent",
            department=self.it,
            created_by=self.other_requester,
            assigned_to=self.technician,
        )

        self.url = reverse("service_desk:dashboard")

    # ------------------------------------------------------------------
    # Authentication / authorization
    # ------------------------------------------------------------------

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_authenticated_user_without_permission_gets_403(self):
        User.objects.create_user(username="nobody", password="password123")
        self.client.login(username="nobody", password="password123")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Context correctness per role
    # ------------------------------------------------------------------

    def test_requester_sees_only_own_tickets(self):
        self.client.login(username="requester", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_tickets"], 2)
        self.assertEqual(response.context["open_tickets"], 1)
        self.assertEqual(response.context["resolved_tickets"], 1)
        self.assertEqual(response.context["closed_tickets"], 0)

        recent = list(response.context["recent_tickets"])
        self.assertIn(self.own_open, recent)
        self.assertNotIn(self.foreign_ticket, recent)
        self.assertNotIn(self.tech_ticket, recent)

    def test_requester_sees_no_problem_data(self):
        Problem.objects.create(
            title="P", description="d", department=self.it
        )

        self.client.login(username="requester", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.context["problem_total"], 0)
        self.assertFalse(response.context["can_view_problems"])

    def test_technician_sees_assigned_and_unassigned_tickets(self):
        self.client.login(username="technician", password="password123")
        response = self.client.get(self.url)

        recent = list(response.context["recent_tickets"])

        # Assigned to them
        self.assertIn(self.tech_ticket, recent)
        # Unassigned tickets are part of the shared queue (ADR-010)
        self.assertIn(self.own_open, recent)
        # Assigned to somebody else — out of scope
        self.assertNotIn(self.hr_assigned, recent)

        self.assertEqual(response.context["total_tickets"], len(recent))
        self.assertEqual(response.context["high_priority_tickets"], 1)

    def test_manager_sees_only_managed_department_tickets(self):
        self.client.login(username="manager", password="password123")
        response = self.client.get(self.url)

        recent = list(response.context["recent_tickets"])

        self.assertIn(self.own_open, recent)
        self.assertIn(self.tech_ticket, recent)
        self.assertNotIn(self.hr_assigned, recent)
        self.assertNotIn(self.foreign_ticket, recent)

        self.assertEqual(response.context["total_tickets"], 3)

    def test_manager_problem_counts_are_department_scoped(self):
        Problem.objects.create(
            title="IT problem", description="d", department=self.it
        )
        Problem.objects.create(
            title="HR problem", description="d", department=self.hr
        )

        self.client.login(username="manager", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.context["problem_total"], 1)
        self.assertTrue(response.context["can_view_problems"])

    def test_administrator_sees_everything(self):
        self.client.login(username="admin", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.context["total_tickets"], 5)
        self.assertEqual(response.context["open_tickets"], 2)
        self.assertEqual(response.context["in_progress_tickets"], 2)
        self.assertEqual(response.context["resolved_tickets"], 1)
        self.assertEqual(response.context["active_tickets"], 4)

    def test_counts_match_the_scoped_queryset_not_the_whole_table(self):
        """The exact leak the dashboard previously risked."""
        self.client.login(username="requester", password="password123")
        response = self.client.get(self.url)

        self.assertNotEqual(
            response.context["total_tickets"], Ticket.objects.count()
        )

    def test_dashboard_renders_recent_ticket_titles(self):
        self.client.login(username="requester", password="password123")
        response = self.client.get(self.url)

        self.assertContains(response, "Own open")
        self.assertNotContains(response, "Foreign ticket")
