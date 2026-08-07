"""
PM-03

Regression coverage for the Problem Management UI milestone:

- Problem is now fully reachable through views/urls/forms/templates,
  not just the ProblemService/ProblemSelector layer built in PM-02.
- ADR-010, Decision 1 (Requesters cannot access Problem records at
  all) is enforced at the view layer, not just the selector.
- The end-to-end workflow (create -> assign -> investigate ->
  RCA auto-creation -> record root cause -> known error -> link
  ticket -> comment -> resolve -> close -> reopen -> unlink) is
  exercised through the real views, not just the service layer
  directly.
"""

from django.test import TestCase, Client

from django.contrib.auth.models import User, Group, Permission

from apps.service_desk.models import (
    Department,
    Problem,
    ProblemHistory,
    RootCauseAnalysis,
    Ticket,
)


class ProblemVisibilityTests(TestCase):
    """
    ADR-010, Decision 1: Requester -> none. Technician -> assigned.
    Manager -> department. Administrator -> all.
    """

    def setUp(self):

        self.client = Client()

        requester_group = Group.objects.create(name="Requester")
        technician_group = Group.objects.create(name="Technician")
        manager_group = Group.objects.create(name="Manager")

        view_problem = Permission.objects.get(codename="view_problem")
        add_problem = Permission.objects.get(codename="add_problem")
        change_problem = Permission.objects.get(codename="change_problem")

        technician_group.permissions.add(view_problem, change_problem)
        manager_group.permissions.add(
            view_problem, add_problem, change_problem
        )
        # Requester intentionally gets none.

        self.requester = User.objects.create_user(
            username="pm03_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.technician = User.objects.create_user(
            username="pm03_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="pm03_manager", password="password123"
        )
        self.manager.groups.add(manager_group)

        self.admin = User.objects.create_superuser(
            username="pm03_admin",
            password="password123",
            email="pm03_admin@test.com",
        )

        self.department = Department.objects.create(name="PM-03 Dept")
        self.department.managers.add(self.manager)

        self.assigned_problem = Problem.objects.create(
            title="Assigned to technician",
            description="x",
            department=self.department,
            assigned_to=self.technician,
        )

        self.department_problem = Problem.objects.create(
            title="Department problem",
            description="x",
            department=self.department,
        )

        self.other_problem = Problem.objects.create(
            title="Unrelated problem",
            description="x",
        )

    def test_requester_cannot_access_problem_list(self):

        self.client.login(
            username="pm03_requester", password="password123"
        )

        response = self.client.get("/problems/")

        self.assertEqual(response.status_code, 403)

    def test_requester_cannot_access_problem_detail(self):

        self.client.login(
            username="pm03_requester", password="password123"
        )

        response = self.client.get(
            f"/problems/{self.department_problem.pk}/"
        )

        self.assertEqual(response.status_code, 403)

    def test_technician_sees_only_assigned_problems(self):

        self.client.login(
            username="pm03_technician", password="password123"
        )

        response = self.client.get("/problems/")

        problems = list(response.context["problems"])

        self.assertIn(self.assigned_problem, problems)
        self.assertNotIn(self.department_problem, problems)
        self.assertNotIn(self.other_problem, problems)

    def test_manager_sees_department_problems(self):

        self.client.login(
            username="pm03_manager", password="password123"
        )

        response = self.client.get("/problems/")

        problems = list(response.context["problems"])

        self.assertIn(self.assigned_problem, problems)
        self.assertIn(self.department_problem, problems)
        self.assertNotIn(self.other_problem, problems)

    def test_admin_sees_all_problems(self):

        self.client.login(
            username="pm03_admin", password="password123"
        )

        response = self.client.get("/problems/")

        self.assertEqual(response.context["problems"].count(), 3)


class ProblemWorkflowViewTests(TestCase):

    def setUp(self):

        self.client = Client()

        manager_group = Group.objects.create(name="Manager")

        view_problem = Permission.objects.get(codename="view_problem")
        add_problem = Permission.objects.get(codename="add_problem")
        change_problem = Permission.objects.get(codename="change_problem")

        manager_group.permissions.add(
            view_problem, add_problem, change_problem
        )

        self.manager = User.objects.create_user(
            username="pm03_wf_manager", password="password123"
        )
        self.manager.groups.add(manager_group)

        self.department = Department.objects.create(
            name="PM-03 Workflow Dept"
        )
        self.department.managers.add(self.manager)

        self.client.login(
            username="pm03_wf_manager", password="password123"
        )

    def test_create_problem_through_view(self):

        response = self.client.post(
            "/problems/new/",
            {
                "title": "Recurring email outage",
                "description": "Email goes down every Monday.",
                "priority": "high",
                "department": self.department.pk,
            },
        )

        self.assertEqual(response.status_code, 302)

        problem = Problem.objects.get(title="Recurring email outage")

        self.assertEqual(problem.status, "open")
        self.assertTrue(
            problem.history.filter(
                event_type=ProblemHistory.EVENT_CREATED
            ).exists()
        )

    def test_full_lifecycle_through_views(self):

        problem = Problem.objects.create(
            title="Lifecycle test problem",
            description="x",
            department=self.department,
        )

        # Investigating -> auto-creates RCA
        response = self.client.post(
            f"/problems/{problem.pk}/status/",
            {"status": "investigating"},
        )
        self.assertEqual(response.status_code, 302)

        problem.refresh_from_db()
        self.assertEqual(problem.status, "investigating")
        self.assertTrue(
            RootCauseAnalysis.objects.filter(problem=problem).exists()
        )

        # Known error blocked without root_cause
        response = self.client.post(
            f"/problems/{problem.pk}/known-error/"
        )
        problem.refresh_from_db()
        self.assertFalse(problem.is_known_error)

        # Record root cause, then known error succeeds
        self.client.post(
            f"/problems/{problem.pk}/root-cause/",
            {"root_cause": "Faulty load balancer config."},
        )

        response = self.client.post(
            f"/problems/{problem.pk}/known-error/"
        )
        self.assertEqual(response.status_code, 302)

        problem.refresh_from_db()
        self.assertTrue(problem.is_known_error)

        # Resolve -> close -> reopen
        self.client.post(
            f"/problems/{problem.pk}/status/",
            {"status": "resolved"},
        )
        self.client.post(f"/problems/{problem.pk}/close/")

        problem.refresh_from_db()
        self.assertEqual(problem.status, "closed")

        self.client.post(f"/problems/{problem.pk}/reopen/")

        problem.refresh_from_db()
        self.assertEqual(problem.status, "open")

    def test_link_and_unlink_ticket(self):

        problem = Problem.objects.create(
            title="Ticket linking test problem",
            description="x",
            department=self.department,
        )

        ticket = Ticket.objects.create(
            title="Related incident",
            description="x",
            department=self.department,
            created_by=self.manager,
        )

        response = self.client.post(
            f"/problems/{problem.pk}/link-ticket/",
            {"ticket_id": ticket.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            problem.related_tickets.filter(pk=ticket.pk).exists()
        )

        response = self.client.post(
            f"/problems/{problem.pk}/unlink-ticket/{ticket.pk}/"
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            problem.related_tickets.filter(pk=ticket.pk).exists()
        )

    def test_detail_page_renders_rca_and_linked_tickets(self):

        problem = Problem.objects.create(
            title="Detail render test problem",
            description="x",
            department=self.department,
        )

        self.client.post(
            f"/problems/{problem.pk}/status/",
            {"status": "investigating"},
        )
        self.client.post(
            f"/problems/{problem.pk}/root-cause/",
            {"root_cause": "Root cause text for rendering check."},
        )

        ticket = Ticket.objects.create(
            title="Linked incident for rendering",
            description="x",
            department=self.department,
            created_by=self.manager,
        )
        self.client.post(
            f"/problems/{problem.pk}/link-ticket/",
            {"ticket_id": ticket.pk},
        )

        response = self.client.get(f"/problems/{problem.pk}/")

        self.assertContains(response, "Root cause text for rendering check.")
        self.assertContains(response, "Linked incident for rendering")
        self.assertContains(response, "Root Cause Analysis")
