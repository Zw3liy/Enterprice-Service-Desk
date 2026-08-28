"""
NAV-01 — navigation, template integrity and dead-UI regression checks.

These are the checks that would have caught the classes of defect this
repository has actually hit before: a view with no route, a route
pointing at a template that does not exist, a nav link to a URL name
that was never registered, and duplicate templates drifting apart.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.test import Client, TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from apps.service_desk.models import Department, Problem, Supplier, Ticket


def _service_desk_patterns():
    """
    Every URL pattern registered under the service_desk namespace.
    """

    resolver = get_resolver()

    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver) and entry.namespace == "service_desk":
            for pattern in entry.url_patterns:
                if isinstance(pattern, URLPattern):
                    yield pattern


class URLAndTemplateIntegrityTests(TestCase):

    def test_every_service_desk_route_points_at_a_real_callable(self):
        patterns = list(_service_desk_patterns())

        self.assertGreater(len(patterns), 20)

        for pattern in patterns:
            with self.subTest(route=str(pattern.pattern)):
                self.assertTrue(callable(pattern.callback))

    def test_every_route_has_a_name(self):
        for pattern in _service_desk_patterns():
            with self.subTest(route=str(pattern.pattern)):
                self.assertIsNotNone(pattern.name)

    def test_every_view_template_exists(self):
        """
        A template_name that does not resolve is a 500 waiting for the
        first user to open that page — IM-02 shipped exactly that bug.
        """

        missing = []

        for pattern in _service_desk_patterns():
            view_class = getattr(pattern.callback, "view_class", None)

            if view_class is None:
                continue

            template_name = getattr(view_class, "template_name", None)

            if not template_name:
                continue

            try:
                get_template(template_name)
            except TemplateDoesNotExist:
                missing.append(
                    f"{view_class.__name__} -> {template_name}"
                )

        self.assertEqual(missing, [])

    def test_admin_module_imports_and_registers_the_live_models(self):
        from django.contrib import admin

        import apps.service_desk.admin  # noqa: F401

        from apps.service_desk.models import (
            CatalogItem,
            Notification,
            ServiceCategory,
            ServiceRequest,
            ServiceRequestApproval,
            SLAEscalation,
            SLAPolicy,
            TicketSLA,
        )

        for model in (
            Department,
            Ticket,
            Supplier,
            SLAPolicy,
            TicketSLA,
            SLAEscalation,
            Notification,
            ServiceCategory,
            CatalogItem,
            ServiceRequest,
            ServiceRequestApproval,
        ):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

    def test_model_package_exports_every_live_model(self):
        from apps.service_desk import models as model_package

        for name in model_package.__all__:
            with self.subTest(model=name):
                self.assertTrue(hasattr(model_package, name))

    def test_removed_duplicate_templates_are_gone(self):
        """
        templates/navbar.html and templates/sidebar.html were byte-level
        duplicates of templates/includes/*; base.html only ever included
        the includes/ pair, so the root copies could drift silently.
        templates/tickets/edit.html was unreachable scaffolding built
        against fields the Ticket model does not have.
        """

        base = Path(settings.BASE_DIR) / "templates"

        for dead in ("navbar.html", "sidebar.html", "tickets/edit.html"):
            with self.subTest(template=dead):
                self.assertFalse((base / dead).exists())

    def test_the_live_navigation_partials_still_exist(self):
        get_template("includes/navbar.html")
        get_template("includes/sidebar.html")
        get_template("base.html")


class NavigationRenderingTests(TestCase):
    """
    The sidebar must offer a role exactly the destinations that role
    can actually open — a link to a 403 is a defect, and a module with
    no link at all is unreachable (IM-02's original bug).
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")

        requester_group = Group.objects.create(name="Requester")
        requester_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )

        manager_group = Group.objects.create(name="Manager")
        manager_group.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "view_ticket",
                    "change_ticket",
                    "view_problem",
                    "change_problem",
                    "view_supplier",
                    "add_supplier",
                    "change_supplier",
                    "view_slapolicy",
                    "add_slapolicy",
                    "change_slapolicy",
                    "view_catalogitem",
                    "add_catalogitem",
                    "change_catalogitem",
                    "view_servicerequest",
                    "change_servicerequest",
                ]
            )
        )

        self.requester = User.objects.create_user(
            username="nav-requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="nav-manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.it.managers.add(self.manager)

    def test_requester_navigation_hides_privileged_modules(self):
        self.client.login(username="nav-requester", password="password123")
        response = self.client.get(reverse("service_desk:dashboard"))

        self.assertContains(response, reverse("service_desk:ticket_list"))
        self.assertContains(response, reverse("service_desk:sla_dashboard"))
        self.assertNotContains(
            response, reverse("service_desk:problem_list")
        )
        self.assertNotContains(
            response, reverse("service_desk:supplier_list")
        )
        self.assertNotContains(
            response, reverse("service_desk:sla_policy_list")
        )

    def test_manager_navigation_exposes_every_authorised_module(self):
        self.client.login(username="nav-manager", password="password123")
        response = self.client.get(reverse("service_desk:dashboard"))

        for name in (
            "ticket_list",
            "incident_dashboard",
            "problem_list",
            "supplier_list",
            "sla_dashboard",
            "sla_policy_list",
            "notification_list",
            "catalog_item_list",
            "service_request_list",
        ):
            with self.subTest(url=name):
                self.assertContains(
                    response, reverse(f"service_desk:{name}")
                )

    def test_every_navigation_destination_opens_for_the_manager(self):
        """
        No dead controls: follow each sidebar link and assert 200.
        """

        self.client.login(username="nav-manager", password="password123")

        for name in (
            "dashboard",
            "ticket_list",
            "incident_dashboard",
            "problem_list",
            "supplier_list",
            "sla_dashboard",
            "sla_policy_list",
            "notification_list",
            "catalog_item_list",
            "service_request_list",
        ):
            with self.subTest(url=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertEqual(response.status_code, 200)

    def test_active_navigation_state_is_marked_for_screen_readers(self):
        self.client.login(username="nav-manager", password="password123")

        response = self.client.get(reverse("service_desk:supplier_list"))

        self.assertContains(response, 'aria-current="page"')

    def test_navigation_is_present_on_every_module_page(self):
        self.client.login(username="nav-manager", password="password123")

        for name in ("problem_list", "supplier_list", "sla_dashboard"):
            with self.subTest(url=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertContains(response, 'aria-label="Main navigation"')
                self.assertContains(response, "Skip to content")

    def test_anonymous_pages_do_not_run_notification_queries(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("nav_unread_notifications", response.context)


class EmptyStateTests(TestCase):
    """
    Every list surface must say something useful when it is empty
    rather than rendering a blank panel.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")

        group = Group.objects.create(name="Manager")
        group.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "view_ticket",
                    "change_ticket",
                    "view_problem",
                    "view_supplier",
                    "view_slapolicy",
                ]
            )
        )

        self.manager = User.objects.create_user(
            username="empty-manager", password="password123"
        )
        self.manager.groups.add(group)
        self.it.managers.add(self.manager)

        self.client.login(username="empty-manager", password="password123")

    def test_dashboard_empty_state(self):
        response = self.client.get(reverse("service_desk:dashboard"))
        self.assertContains(response, "No tickets found")

    def test_supplier_list_empty_state(self):
        response = self.client.get(reverse("service_desk:supplier_list"))
        self.assertContains(response, "No suppliers found")

    def test_sla_policy_list_empty_state(self):
        response = self.client.get(reverse("service_desk:sla_policy_list"))
        self.assertContains(response, "No SLA policies are configured")

    def test_sla_dashboard_empty_state(self):
        response = self.client.get(reverse("service_desk:sla_dashboard"))
        self.assertContains(response, "No breached SLAs")

    def test_notification_inbox_empty_state(self):
        response = self.client.get(
            reverse("service_desk:notification_list")
        )
        self.assertContains(response, "You have no notifications")

    def test_problem_list_renders_for_an_empty_scope(self):
        response = self.client.get(reverse("service_desk:problem_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 0)
