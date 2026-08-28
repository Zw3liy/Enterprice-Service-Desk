"""
Enterprise Completion Program — Phase 7: Reporting and Analytics.

Covers: CSV formula-injection sanitisation (the mission's explicit
"safe CSV export" requirement), exports and dashboard sections using
the exact same RBAC-scoped queryset as the owning module's own UI (no
separate, wider reporting data path), department/date filtering,
bounded query count on export (N+1 avoidance), anonymous redirect,
and unauthorized-export rejection.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import Department, Ticket
from apps.service_desk.services.reporting_service import sanitize_csv_cell


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class CSVSanitizationTests(TestCase):
    def test_formula_prefixes_are_neutralised(self):
        for dangerous in ("=cmd()", "+1+1", "-1-1", "@SUM(A1)", "\ttab", "\rcr"):
            with self.subTest(value=dangerous):
                sanitized = sanitize_csv_cell(dangerous)
                self.assertTrue(sanitized.startswith("'"))
                self.assertEqual(sanitized[1:], dangerous)

    def test_ordinary_text_is_untouched(self):
        self.assertEqual(sanitize_csv_cell("Router upgrade"), "Router upgrade")

    def test_none_becomes_empty_string(self):
        self.assertEqual(sanitize_csv_cell(None), "")

    def test_numbers_are_stringified_safely(self):
        self.assertEqual(sanitize_csv_cell(42), "42")


class ReportingDashboardScopeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")
        self.other_dept = Department.objects.create(name="Finance")

        requester_group = Group.objects.create(name="Requester")
        _grant(requester_group, "view_ticket", "add_ticket")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_ticket", "view_change", "view_release")

        self.requester = User.objects.create_user(
            username="rpt_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="rpt_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.own_ticket = Ticket.objects.create(
            title="My ticket", description="x", created_by=self.requester,
        )
        self.other_ticket = Ticket.objects.create(
            title="Someone else's ticket", description="x",
            department=self.dept,
        )
        self.unrelated_dept_ticket = Ticket.objects.create(
            title="Finance ticket", description="x", department=self.other_dept,
        )

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:reporting_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requester_ticket_stats_only_count_their_own(self):
        self.client.login(username="rpt_requester", password="password123")
        response = self.client.get(reverse("service_desk:reporting_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ticket_stats"]["total"], 1)

    def test_requester_sees_no_change_or_release_section(self):
        self.client.login(username="rpt_requester", password="password123")
        response = self.client.get(reverse("service_desk:reporting_dashboard"))
        self.assertNotIn("change_stats", response.context)
        self.assertNotIn("release_stats", response.context)

    def test_manager_ticket_stats_are_department_scoped(self):
        self.client.login(username="rpt_manager", password="password123")
        response = self.client.get(reverse("service_desk:reporting_dashboard"))
        # sees their department ticket, not the requester's or Finance's
        self.assertEqual(response.context["ticket_stats"]["total"], 1)

    def test_department_filter_narrows_further(self):
        second_dept_ticket = Ticket.objects.create(
            title="Second dept ticket", description="x", department=self.dept,
        )
        self.client.login(username="rpt_manager", password="password123")
        response = self.client.get(
            reverse("service_desk:reporting_dashboard"),
            {"department": self.dept.pk},
        )
        self.assertEqual(response.context["ticket_stats"]["total"], 2)

    def test_date_range_excludes_out_of_window_records(self):
        self.client.login(username="rpt_manager", password="password123")
        response = self.client.get(
            reverse("service_desk:reporting_dashboard"),
            {"date_from": "2099-01-01"},
        )
        self.assertEqual(response.context["ticket_stats"]["total"], 0)


class ReportingExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")

        requester_group = Group.objects.create(name="Requester")
        _grant(requester_group, "view_ticket", "add_ticket")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_ticket")

        self.requester = User.objects.create_user(
            username="exp_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="exp_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.own_ticket = Ticket.objects.create(
            title="My ticket", description="x", created_by=self.requester,
        )
        self.dept_ticket = Ticket.objects.create(
            title="=cmd|'/c calc'!A1", description="x", department=self.dept,
        )

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:reporting_export_tickets"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_export_uses_the_same_scoped_queryset_as_the_ui(self):
        self.client.login(username="exp_requester", password="password123")
        response = self.client.get(reverse("service_desk:reporting_export_tickets"))
        self.assertEqual(response.status_code, 200)

        content = b"".join(response.streaming_content).decode()
        self.assertIn("My ticket", content)
        self.assertNotIn("cmd", content)  # the department ticket, out of scope

    def test_malicious_title_is_neutralised_in_the_csv(self):
        self.client.login(username="exp_manager", password="password123")
        response = self.client.get(reverse("service_desk:reporting_export_tickets"))
        content = b"".join(response.streaming_content).decode()

        # the raw formula-triggering title must never appear un-prefixed
        self.assertNotIn(",=cmd", content)
        self.assertIn("'=cmd", content)

    def test_export_is_csv_content_type(self):
        self.client.login(username="exp_requester", password="password123")
        response = self.client.get(reverse("service_desk:reporting_export_tickets"))
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_unauthorized_export_is_rejected(self):
        """
        The Requester holds view_ticket but not view_change — the
        Change export must not silently return an empty file, it
        must reject the request outright.
        """

        self.client.login(username="exp_requester", password="password123")
        response = self.client.get(reverse("service_desk:reporting_export_changes"))
        self.assertEqual(response.status_code, 403)

    def test_export_query_count_does_not_grow_with_row_count(self):
        """
        N+1 avoidance: the query count for exporting a handful of
        tickets must be the same as exporting many more — proven by
        comparison rather than a hardcoded count, since the exact
        number includes incidental auth/permission-cache queries
        that are irrelevant to what this test is actually checking.
        """

        self.client.login(username="exp_requester", password="password123")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as small_capture:
            response = self.client.get(
                reverse("service_desk:reporting_export_tickets")
            )
            b"".join(response.streaming_content)

        for i in range(20):
            Ticket.objects.create(
                title=f"Bulk ticket {i}", description="x",
                created_by=self.requester,
            )

        with CaptureQueriesContext(connection) as large_capture:
            response = self.client.get(
                reverse("service_desk:reporting_export_tickets")
            )
            b"".join(response.streaming_content)

        self.assertEqual(len(small_capture), len(large_capture))
