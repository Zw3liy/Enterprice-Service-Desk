"""
Enterprise Service Desk
Service Desk View Tests

Phase 2.2 RBAC Enforcement Compatible

"""

from django.test import TestCase, Client
from django.urls import reverse

from django.contrib.auth.models import (
    User,
    Group,
    Permission,
)

from apps.service_desk.models import (
    Ticket,
    Department,
)



class ServiceDeskViewTests(TestCase):


    def setUp(self):

        self.client = Client()


        # =====================================================
        # USER
        # =====================================================

        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )


        # =====================================================
        # RBAC GROUP
        # =====================================================

        technician_group, _ = Group.objects.get_or_create(
            name="Technician"
        )


        self.user.groups.add(
            technician_group
        )


        # =====================================================
        # DJANGO MODEL PERMISSIONS
        # =====================================================

        permissions = Permission.objects.filter(
            content_type__app_label="service_desk",
            codename__in=[
                "view_ticket",
                "add_ticket",
                "change_ticket",
            ]
        )


        technician_group.permissions.add(
            *permissions
        )


        # =====================================================
        # DEPARTMENT
        # =====================================================

        self.department = Department.objects.create(
            name="IT",
            description="Information Technology"
        )


        # =====================================================
        # TICKET
        # =====================================================

        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            description="Test Description",
            created_by=self.user,
            assigned_to=self.user,
            department=self.department,
        )


        # =====================================================
        # LOGIN
        # =====================================================

        self.client.login(
            username="testuser",
            password="password123"
        )



    def test_dashboard(self):

        response = self.client.get(
            reverse(
                "service_desk:dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )



    def test_ticket_list(self):

        response = self.client.get(
            reverse(
                "service_desk:ticket_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )



    def test_ticket_detail(self):

        response = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                args=[
                    self.ticket.id
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )



    def test_ticket_create_page(self):

        response = self.client.get(
            reverse(
                "service_desk:ticket_create"
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )