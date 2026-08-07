"""
Enterprise Service Desk

Phase 2.2 Authorization Policy Tests

Validates:

Administrator:
    Full system visibility

Manager:
    Department scoped visibility

Technician:
    Assigned ticket visibility

Requester:
    Created ticket visibility

"""

from django.test import TestCase

from django.contrib.auth.models import User, Group

from apps.service_desk.models import (
    Ticket,
    Department,
)

from apps.service_desk.security.policies import (
    get_ticket_queryset,
)



class AuthorizationPolicyTests(TestCase):


    def setUp(self):

        # =====================================================
        # USERS
        # =====================================================

        self.requester = User.objects.create_user(
            username="requester",
            password="password123"
        )


        self.technician = User.objects.create_user(
            username="technician",
            password="password123"
        )


        self.other_technician = User.objects.create_user(
            username="other_technician",
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


        # =====================================================
        # GROUPS
        # =====================================================

        requester_group = Group.objects.get_or_create(
            name="Requester"
        )[0]


        technician_group = Group.objects.get_or_create(
            name="Technician"
        )[0]


        manager_group = Group.objects.get_or_create(
            name="Manager"
        )[0]


        self.requester.groups.add(
            requester_group
        )

        self.technician.groups.add(
            technician_group
        )

        self.manager.groups.add(
            manager_group
        )


        # =====================================================
        # DEPARTMENTS
        # =====================================================


        self.it_department = Department.objects.create(
            name="IT",
            description="Information Technology"
        )


        self.finance_department = Department.objects.create(
            name="Finance",
            description="Finance Department"
        )


        self.finance_department.managers.add(
            self.manager
        )


        # =====================================================
        # TICKETS
        # =====================================================


        # Requester owns this
        self.requester_ticket = Ticket.objects.create(
            title="Requester Ticket",
            description="Created by requester",
            created_by=self.requester,
            department=self.it_department
        )


        # Technician assigned ticket
        self.assigned_ticket = Ticket.objects.create(
    title="Technician Ticket",
    description="Assigned technician ticket",
    created_by=self.manager,
    assigned_to=self.technician,
    department=self.it_department
)


        # Manager department ticket
        self.manager_ticket = Ticket.objects.create(
    title="Manager Department Ticket",
    description="Finance department ticket",
    created_by=self.manager,
    department=self.finance_department
)


        # unrelated ticket
        self.private_ticket = Ticket.objects.create(
            title="Private Ticket",
            description="Another department",
            created_by=self.technician,
            department=self.it_department
        )


        # Assigned to a different technician — should stay excluded
        # even though Technicians now also see unassigned tickets
        # (ADR-010, Decision 2).
        self.other_technician_ticket = Ticket.objects.create(
            title="Other Technician's Ticket",
            description="Assigned to a different technician",
            created_by=self.manager,
            assigned_to=self.other_technician,
            department=self.it_department
        )



    # =====================================================
    # REQUESTER
    # =====================================================

    def test_requester_only_sees_owned_tickets(self):

        tickets = get_ticket_queryset(
            self.requester
        )


        self.assertIn(
            self.requester_ticket,
            tickets
        )


        self.assertNotIn(
            self.manager_ticket,
            tickets
        )



    # =====================================================
    # TECHNICIAN
    # =====================================================

    def test_technician_sees_assigned_and_unassigned_tickets(self):

        # ADR-010, Decision 2: Technicians see tickets assigned to
        # them, plus unassigned tickets (queue-based
        # self-assignment) — but not tickets assigned to someone
        # else.

        tickets = get_ticket_queryset(
            self.technician
        )


        self.assertIn(
            self.assigned_ticket,
            tickets
        )


        self.assertIn(
            self.manager_ticket,
            tickets
        )


        self.assertNotIn(
            self.other_technician_ticket,
            tickets
        )



    # =====================================================
    # MANAGER
    # =====================================================

    def test_manager_sees_department_tickets(self):

        tickets = get_ticket_queryset(
            self.manager
        )


        self.assertIn(
            self.manager_ticket,
            tickets
        )


        self.assertNotIn(
            self.private_ticket,
            tickets
        )



    # =====================================================
    # ADMIN
    # =====================================================

    def test_admin_sees_all_tickets(self):

        tickets = get_ticket_queryset(
            self.admin
        )


        self.assertEqual(
            tickets.count(),
            5
        )