"""
IM-02

Regression coverage for the Incident Dashboard stabilization:

- The view previously had no URL route at all (unreachable).
- Its template ("service_desk/incidents.html") did not exist.
- Its status/priority filters used uppercase and invented values
  ("UNASSIGNED", "CRITICAL") that never matched the real lowercase
  Ticket.STATUS_CHOICES / PRIORITY_CHOICES, so the dashboard's own
  counts were always wrong.
- Its queryset was unscoped (Ticket.objects), bypassing the RBAC
  scoping every other ticket view in this module applies.
"""

from django.test import TestCase, Client

from django.contrib.auth.models import User, Group, Permission

from apps.service_desk.models import Department, Ticket


class IncidentDashboardTests(TestCase):

    def setUp(self):

        self.client = Client()

        requester_group = Group.objects.create(name="Requester")

        view_ticket = Permission.objects.get(codename="view_ticket")

        requester_group.permissions.add(view_ticket)

        self.requester = User.objects.create_user(
            username="im02_requester",
            password="password123",
        )

        self.requester.groups.add(requester_group)

        self.admin = User.objects.create_superuser(
            username="im02_admin",
            password="password123",
            email="im02_admin@test.com",
        )

        self.department = Department.objects.create(
            name="IM-02 Department",
        )

        self.own_ticket = Ticket.objects.create(
            title="Requester's own incident",
            description="Owned by requester",
            status="open",
            priority="urgent",
            created_by=self.requester,
            department=self.department,
        )

        self.other_ticket = Ticket.objects.create(
            title="Someone else's incident",
            description="Not visible to requester",
            status="pending",
            priority="low",
            created_by=self.admin,
            department=self.department,
        )

    def test_dashboard_is_reachable(self):

        self.client.login(
            username="im02_admin",
            password="password123",
        )

        response = self.client.get("/incidents/")

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_access_dashboard(self):

        # ServiceDeskPermissionMixin.handle_no_permission splits the
        # two failure modes: an anonymous visitor is redirected to the
        # login page (they have not identified themselves yet), while
        # an *authenticated* user missing the permission still gets a
        # hard 403 (asserted below). Either way no ticket data is
        # served.
        response = self.client.get("/incidents/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertNotIn("incidents", getattr(response, "context", {}) or {})

    def test_authenticated_user_without_permission_gets_403(self):

        User.objects.create_user(
            username="im02_nopermission",
            password="password123",
        )

        self.client.login(
            username="im02_nopermission",
            password="password123",
        )

        response = self.client.get("/incidents/")

        self.assertEqual(response.status_code, 403)

    def test_requester_only_sees_own_tickets_on_dashboard(self):

        self.client.login(
            username="im02_requester",
            password="password123",
        )

        response = self.client.get("/incidents/")

        incidents = list(response.context["incidents"])

        self.assertIn(self.own_ticket, incidents)
        self.assertNotIn(self.other_ticket, incidents)
        self.assertEqual(response.context["total_incidents"], 1)

    def test_admin_sees_all_tickets_on_dashboard(self):

        self.client.login(
            username="im02_admin",
            password="password123",
        )

        response = self.client.get("/incidents/")

        self.assertEqual(response.context["total_incidents"], 2)

    def test_pending_incidents_uses_real_status_values(self):

        self.client.login(
            username="im02_admin",
            password="password123",
        )

        response = self.client.get("/incidents/")

        pending = list(response.context["pending_incidents"])

        # "open" and "pending" are both real, non-terminal statuses.
        self.assertIn(self.own_ticket, pending)
        self.assertIn(self.other_ticket, pending)

    def test_critical_incidents_uses_real_priority_values(self):

        self.client.login(
            username="im02_admin",
            password="password123",
        )

        response = self.client.get("/incidents/")

        critical = list(response.context["critical_incidents"])

        self.assertIn(self.own_ticket, critical)
        self.assertNotIn(self.other_ticket, critical)
