"""
Enterprise Service Desk
Authorization Tests

Validates object-level security rules.

Phase 2.2.3
"""

from django.test import TestCase
from django.contrib.auth.models import User

from apps.service_desk.models import (
    Ticket,
    Department,
)

from apps.service_desk.security.policies import (
    get_ticket_queryset,
)



class AuthorizationPolicyTests(TestCase):
    

    def setUp(self):

        # Users

        self.requester_one = User.objects.create_user(
            username="requester_one",
            password="password123"
        )


        self.requester_two = User.objects.create_user(
            username="requester_two",
            password="password123"
        )


        self.technician = User.objects.create_user(
            username="technician",
            password="password123"
        )


        self.manager = User.objects.create_user(
            username="manager",
            password="password123"
        )


        self.admin = User.objects.create_superuser(
            username="admin",
            password="password123",
            email="admin@test.com"
        )


        # Departments

        self.it_department = Department.objects.create(
            name="IT"
        )


        self.hr_department = Department.objects.create(
            name="HR"
        )


        self.it_department.managers.add(
            self.manager
        )


        # Tickets

        self.requester_ticket = Ticket.objects.create(
            title="Requester Ticket",
            description="Created by requester",
            created_by=self.requester_one,
            department=self.hr_department,
        )


        self.other_requester_ticket = Ticket.objects.create(
            title="Other Requester Ticket",
            description="Created by another requester",
            created_by=self.requester_two,
            department=self.hr_department,
        )


        self.assigned_ticket = Ticket.objects.create(
            title="Technician Ticket",
            description="Assigned ticket",
            assigned_to=self.technician,
            department=self.it_department,
        )


        self.manager_ticket = Ticket.objects.create(
            title="Manager Department Ticket",
            description="Department ticket",
            department=self.it_department,
        )


        self.other_department_ticket = Ticket.objects.create(
            title="HR Ticket",
            description="Other department",
            department=self.hr_department,
        )



    def test_requester_only_sees_owned_tickets(self):

        tickets = get_ticket_queryset(
            self.requester_one
        )


        self.assertIn(
            self.requester_ticket,
            tickets
        )


        self.assertNotIn(
            self.other_requester_ticket,
            tickets
        )



    def test_technician_only_sees_assigned_tickets(self):

        tickets = get_ticket_queryset(
            self.technician
        )


        self.assertIn(
            self.assigned_ticket,
            tickets
        )


        self.assertNotIn(
            self.requester_ticket,
            tickets
        )



    def test_manager_sees_department_tickets(self):

        tickets = get_ticket_queryset(
            self.manager
        )


        self.assertIn(
            self.manager_ticket,
            tickets
        )


        self.assertNotIn(
            self.other_department_ticket,
            tickets
        )



    def test_administrator_sees_all_tickets(self):

        tickets = get_ticket_queryset(
            self.admin
        )


        self.assertEqual(
            tickets.count(),
            Ticket.objects.count()
        )