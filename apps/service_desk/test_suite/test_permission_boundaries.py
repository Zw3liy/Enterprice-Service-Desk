"""
apps/service_desk/tests/test_permission_boundaries.py

Phase 2.2.4 — Authorization Hardening

Permission boundary verification.

Validates:
- RBAC permissions
- denied actions
- allowed actions
- administrator bypass
"""


from django.test import TestCase, Client

from django.contrib.auth.models import (
    User,
    Group,
    Permission,
)

from apps.service_desk.models import (
    Ticket,
    Department,
)


class PermissionBoundaryTests(TestCase):

    def setUp(self):

        self.client = Client()


        # --------------------------------------------------
        # Create RBAC Groups
        # --------------------------------------------------

        requester_group = Group.objects.create(
            name="Requester"
        )

        technician_group = Group.objects.create(
            name="Technician"
        )


        # --------------------------------------------------
        # Permissions
        # --------------------------------------------------

        view_ticket = Permission.objects.get(
            codename="view_ticket"
        )

        add_ticket = Permission.objects.get(
            codename="add_ticket"
        )

        change_ticket = Permission.objects.get(
            codename="change_ticket"
        )


        requester_group.permissions.add(
            view_ticket
        )


        technician_group.permissions.add(
            view_ticket,
            change_ticket,
        )


        # --------------------------------------------------
        # Users
        # --------------------------------------------------

        self.requester = User.objects.create_user(
            username="requester",
            password="password123"
        )


        self.requester.groups.add(
            requester_group
        )


        self.technician = User.objects.create_user(
            username="technician",
            password="password123"
        )


        self.technician.groups.add(
            technician_group
        )


        self.admin = User.objects.create_superuser(
            username="admin",
            password="password123",
            email="admin@test.com"
        )


        self.no_permission_user = User.objects.create_user(
            username="noperms",
            password="password123"
        )


        # --------------------------------------------------
        # Domain Data
        # --------------------------------------------------

        self.department = Department.objects.create(
            name="IT"
        )


        self.ticket = Ticket.objects.create(
            title="Authorization Test Ticket",
            description="Testing permissions",
            created_by=self.requester,
            assigned_to=self.technician,
            department=self.department,
        )


    # --------------------------------------------------
    # Permission Tests
    # --------------------------------------------------

    def test_requester_without_add_permission_cannot_create_ticket(self):

        self.client.login(
            username="requester",
            password="password123"
        )


        response = self.client.get(
            "/tickets/new/"
        )


        self.assertEqual(
            response.status_code,
            403
        )


    def test_user_without_view_permission_cannot_access_ticket_list(self):

        self.client.login(
            username="noperms",
            password="password123"
        )


        response = self.client.get(
            "/tickets/"
        )


        self.assertEqual(
            response.status_code,
            403
        )


    def test_technician_with_view_permission_can_access_ticket_list(self):

        self.client.login(
            username="technician",
            password="password123"
        )


        response = self.client.get(
            "/tickets/"
        )


        self.assertEqual(
            response.status_code,
            200
        )


    def test_admin_can_access_ticket_create(self):

        self.client.login(
            username="admin",
            password="password123"
        )


        response = self.client.get(
            "/tickets/new/"
        )


        self.assertEqual(
            response.status_code,
            200
        )