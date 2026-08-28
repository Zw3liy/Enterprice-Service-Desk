"""
Authoritative route matrix — authentication, 403/404 and role visibility.

For every registered service_desk route that is safe to GET without path
parameters, and for a representative set of object-scoped routes:

- anonymous users are redirected to login;
- authenticated users missing the permission receive 403;
- authorised roles receive 200 (or the documented redirect);
- cross-department object access yields 404 without content leakage;
- nonexistent objects yield 404.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import (
    Department,
    Problem,
    RequestType,
    SLAPolicy,
    Supplier,
    Ticket,
)


class RouteRBACMatrixTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT Route")
        self.hr = Department.objects.create(name="HR Route")

        RequestType.objects.create(name="Incident", is_active=True)

        # Build the four standard roles with create_roles-equivalent perms.
        self.roles = {}
        for name in ("Requester", "Technician", "Manager", "Administrator"):
            self.roles[name] = Group.objects.create(name=name)

        ticket_perms = {
            c: Permission.objects.get(codename=c)
            for c in ("view_ticket", "add_ticket", "change_ticket", "delete_ticket")
        }
        problem_perms = {
            c: Permission.objects.get(codename=c)
            for c in (
                "view_problem",
                "add_problem",
                "change_problem",
                "delete_problem",
            )
        }
        supplier_perms = {
            c: Permission.objects.get(codename=c)
            for c in (
                "view_supplier",
                "add_supplier",
                "change_supplier",
                "delete_supplier",
            )
        }
        sla_perms = {
            c: Permission.objects.get(codename=c)
            for c in (
                "view_slapolicy",
                "add_slapolicy",
                "change_slapolicy",
                "delete_slapolicy",
            )
        }

        self.roles["Requester"].permissions.set(
            [ticket_perms["view_ticket"], ticket_perms["add_ticket"]]
        )
        self.roles["Technician"].permissions.set(
            [
                ticket_perms["view_ticket"],
                ticket_perms["add_ticket"],
                ticket_perms["change_ticket"],
                problem_perms["view_problem"],
                problem_perms["add_problem"],
                problem_perms["change_problem"],
            ]
        )
        self.roles["Manager"].permissions.set(
            [
                ticket_perms["view_ticket"],
                ticket_perms["add_ticket"],
                ticket_perms["change_ticket"],
                problem_perms["view_problem"],
                problem_perms["add_problem"],
                problem_perms["change_problem"],
                supplier_perms["view_supplier"],
                supplier_perms["add_supplier"],
                supplier_perms["change_supplier"],
                sla_perms["view_slapolicy"],
                sla_perms["add_slapolicy"],
                sla_perms["change_slapolicy"],
            ]
        )
        self.roles["Administrator"].permissions.set(
            list(ticket_perms.values())
            + list(problem_perms.values())
            + list(supplier_perms.values())
            + list(sla_perms.values())
        )

        self.requester = User.objects.create_user(
            username="rbac_req", password="pass123"
        )
        self.requester.groups.add(self.roles["Requester"])

        self.technician = User.objects.create_user(
            username="rbac_tech", password="pass123"
        )
        self.technician.groups.add(self.roles["Technician"])

        self.manager = User.objects.create_user(
            username="rbac_mgr", password="pass123"
        )
        self.manager.groups.add(self.roles["Manager"])
        self.it.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="rbac_mgr_hr", password="pass123"
        )
        self.other_manager.groups.add(self.roles["Manager"])
        self.hr.managers.add(self.other_manager)

        self.admin = User.objects.create_user(
            username="rbac_admin", password="pass123", is_superuser=True
        )
        self.admin.groups.add(self.roles["Administrator"])

        self.own_ticket = Ticket.objects.create(
            title="Requester own ticket",
            description="visible to requester",
            department=self.it,
            created_by=self.requester,
        )
        self.foreign_ticket = Ticket.objects.create(
            title="Secret Foreign Ticket XYZ",
            description="must not leak",
            department=self.hr,
            created_by=self.other_manager,
        )
        self.unassigned = Ticket.objects.create(
            title="Unassigned queue ticket",
            description="technician may claim",
            department=self.it,
            assigned_to=None,
        )

        self.problem = Problem.objects.create(
            title="IT Problem",
            description="scoped to IT",
            department=self.it,
            created_by=self.manager,
            assigned_to=self.technician,
        )
        self.hr_problem = Problem.objects.create(
            title="HR Secret Problem",
            description="must not leak",
            department=self.hr,
            created_by=self.other_manager,
        )

        self.supplier = Supplier.objects.create(
            name="IT Supplier",
            department=self.it,
            is_active=True,
        )
        self.hr_supplier = Supplier.objects.create(
            name="HR Secret Supplier",
            department=self.hr,
            is_active=True,
        )

        self.policy = SLAPolicy.objects.create(
            name="Global Medium",
            priority="medium",
            response_minutes=60,
            resolution_minutes=240,
        )

    def _login(self, user):
        assert self.client.login(username=user.username, password="pass123")

    # ------------------------------------------------------------------
    # Anonymous
    # ------------------------------------------------------------------

    def test_anonymous_list_routes_redirect_to_login(self):
        for name in (
            "dashboard",
            "ticket_list",
            "ticket_create",
            "incident_dashboard",
            "problem_list",
            "problem_create",
            "supplier_list",
            "supplier_create",
            "sla_dashboard",
            "sla_policy_list",
            "sla_policy_create",
            "notification_list",
        ):
            with self.subTest(route=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/login/", response["Location"])

    def test_anonymous_object_routes_redirect_to_login(self):
        routes = [
            reverse("service_desk:ticket_detail", kwargs={"pk": self.own_ticket.pk}),
            reverse("service_desk:problem_detail", kwargs={"pk": self.problem.pk}),
            reverse("service_desk:supplier_detail", kwargs={"pk": self.supplier.pk}),
        ]
        for url in routes:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/login/", response["Location"])

    # ------------------------------------------------------------------
    # Requester
    # ------------------------------------------------------------------

    def test_requester_allowed_routes_return_200(self):
        self._login(self.requester)
        for name in (
            "dashboard",
            "ticket_list",
            "ticket_create",
            "incident_dashboard",
            "sla_dashboard",
            "notification_list",
        ):
            with self.subTest(route=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertEqual(response.status_code, 200)

    def test_requester_denied_privileged_routes(self):
        self._login(self.requester)
        for name in (
            "problem_list",
            "problem_create",
            "supplier_list",
            "supplier_create",
            "sla_policy_list",
            "sla_policy_create",
        ):
            with self.subTest(route=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertEqual(response.status_code, 403)

    def test_requester_sees_own_ticket_not_foreign(self):
        self._login(self.requester)
        own = self.client.get(
            reverse("service_desk:ticket_detail", kwargs={"pk": self.own_ticket.pk})
        )
        self.assertEqual(own.status_code, 200)

        foreign = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                kwargs={"pk": self.foreign_ticket.pk},
            )
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertNotContains(
            foreign, "Secret Foreign Ticket XYZ", status_code=404
        )

    def test_requester_navigation_hides_privileged_links(self):
        self._login(self.requester)
        response = self.client.get(reverse("service_desk:dashboard"))
        self.assertContains(response, reverse("service_desk:ticket_list"))
        self.assertContains(response, reverse("service_desk:ticket_create"))
        self.assertNotContains(response, reverse("service_desk:problem_list"))
        self.assertNotContains(response, reverse("service_desk:supplier_list"))
        self.assertNotContains(
            response, reverse("service_desk:sla_policy_list")
        )

    # ------------------------------------------------------------------
    # Technician
    # ------------------------------------------------------------------

    def test_technician_can_open_problems_and_tickets(self):
        self._login(self.technician)
        for name in (
            "dashboard",
            "ticket_list",
            "ticket_create",
            "problem_list",
            "problem_create",
            "incident_dashboard",
            "sla_dashboard",
        ):
            with self.subTest(route=name):
                self.assertEqual(
                    self.client.get(reverse(f"service_desk:{name}")).status_code,
                    200,
                )

        # Assigned problem visible; supplier still 403.
        self.assertEqual(
            self.client.get(
                reverse(
                    "service_desk:problem_detail", kwargs={"pk": self.problem.pk}
                )
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("service_desk:supplier_list")).status_code,
            403,
        )

    def test_technician_sees_unassigned_queue(self):
        self._login(self.technician)
        response = self.client.get(
            reverse(
                "service_desk:ticket_detail", kwargs={"pk": self.unassigned.pk}
            )
        )
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Manager — department scope
    # ------------------------------------------------------------------

    def test_manager_scoped_to_managed_departments(self):
        self._login(self.manager)

        # IT ticket (unassigned in managed dept) — managers see dept tickets.
        it_ticket = Ticket.objects.create(
            title="IT dept ticket",
            description="in scope",
            department=self.it,
            created_by=self.requester,
        )
        self.assertEqual(
            self.client.get(
                reverse("service_desk:ticket_detail", kwargs={"pk": it_ticket.pk})
            ).status_code,
            200,
        )

        foreign = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                kwargs={"pk": self.foreign_ticket.pk},
            )
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertNotContains(
            foreign, "Secret Foreign Ticket XYZ", status_code=404
        )

        self.assertEqual(
            self.client.get(
                reverse(
                    "service_desk:supplier_detail",
                    kwargs={"pk": self.supplier.pk},
                )
            ).status_code,
            200,
        )
        hr_sup = self.client.get(
            reverse(
                "service_desk:supplier_detail",
                kwargs={"pk": self.hr_supplier.pk},
            )
        )
        self.assertEqual(hr_sup.status_code, 404)
        self.assertNotContains(hr_sup, "HR Secret Supplier", status_code=404)

        hr_prob = self.client.get(
            reverse(
                "service_desk:problem_detail",
                kwargs={"pk": self.hr_problem.pk},
            )
        )
        self.assertEqual(hr_prob.status_code, 404)
        self.assertNotContains(hr_prob, "HR Secret Problem", status_code=404)

    def test_manager_navigation_exposes_authorised_modules(self):
        self._login(self.manager)
        response = self.client.get(reverse("service_desk:dashboard"))
        for name in (
            "ticket_list",
            "problem_list",
            "supplier_list",
            "sla_dashboard",
            "sla_policy_list",
            "notification_list",
        ):
            with self.subTest(url=name):
                self.assertContains(response, reverse(f"service_desk:{name}"))

    # ------------------------------------------------------------------
    # Administrator
    # ------------------------------------------------------------------

    def test_administrator_sees_cross_department_objects(self):
        self._login(self.admin)
        for url in (
            reverse(
                "service_desk:ticket_detail",
                kwargs={"pk": self.foreign_ticket.pk},
            ),
            reverse(
                "service_desk:problem_detail",
                kwargs={"pk": self.hr_problem.pk},
            ),
            reverse(
                "service_desk:supplier_detail",
                kwargs={"pk": self.hr_supplier.pk},
            ),
            reverse("service_desk:sla_policy_list"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    # ------------------------------------------------------------------
    # 404 — nonexistent
    # ------------------------------------------------------------------

    def test_nonexistent_objects_are_404(self):
        self._login(self.admin)
        for name, kwargs in (
            ("ticket_detail", {"pk": 999999}),
            ("problem_detail", {"pk": 999999}),
            ("supplier_detail", {"pk": 999999}),
            ("sla_policy_update", {"pk": 999999}),
        ):
            with self.subTest(route=name):
                response = self.client.get(
                    reverse(f"service_desk:{name}", kwargs=kwargs)
                )
                self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # POST-only state changes
    # ------------------------------------------------------------------

    def test_state_changing_endpoints_reject_get(self):
        self._login(self.technician)
        endpoints = [
            reverse(
                "service_desk:ticket_assign", kwargs={"pk": self.unassigned.pk}
            ),
            reverse(
                "service_desk:ticket_status_change",
                kwargs={"pk": self.unassigned.pk},
            ),
            reverse(
                "service_desk:ticket_comment",
                kwargs={"pk": self.unassigned.pk},
            ),
            reverse(
                "service_desk:notification_read_all",
            ),
        ]
        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 405)
