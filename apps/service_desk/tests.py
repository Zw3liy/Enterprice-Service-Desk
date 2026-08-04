from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Department, RequestType, Ticket


User = get_user_model()


class DepartmentModelTests(TestCase):

    def test_create_department(self):
        department = Department.objects.create(
            name="Information Technology",
            description="IT Department"
        )

        self.assertEqual(str(department), "Information Technology")
        self.assertEqual(Department.objects.count(), 1)


class RequestTypeModelTests(TestCase):

    def test_create_request_type(self):
        request_type = RequestType.objects.create(
            name="Incident",
            description="Incident Request"
        )

        self.assertEqual(str(request_type), "Incident")
        self.assertEqual(RequestType.objects.count(), 1)


class TicketModelTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="tester",
            password="password123"
        )

        self.department = Department.objects.create(
            name="IT"
        )

        self.request_type = RequestType.objects.create(
            name="Incident"
        )

    def test_create_ticket(self):

        ticket = Ticket.objects.create(

            title="Cannot connect to VPN",

            description="VPN authentication fails.",

            department=self.department,

            request_type=self.request_type,

            created_by=self.user,

            assigned_to=self.user,

        )

        self.assertEqual(ticket.priority, "medium")
        self.assertEqual(ticket.urgency, "medium")
        self.assertEqual(ticket.status, "open")

        self.assertEqual(ticket.department, self.department)
        self.assertEqual(ticket.request_type, self.request_type)

        self.assertEqual(
            str(ticket),
            f"[{ticket.pk}] Cannot connect to VPN"
        )

    def test_default_values(self):

        ticket = Ticket.objects.create(

            title="Printer Offline",

            description="Printer not responding"

        )

        self.assertEqual(ticket.priority, "medium")
        self.assertEqual(ticket.urgency, "medium")
        self.assertEqual(ticket.status, "open")

    def test_ticket_ordering(self):

        Ticket.objects.create(
            title="Old",
            description="Old"
        )

        Ticket.objects.create(
            title="New",
            description="New"
        )

        tickets = Ticket.objects.all()

        self.assertEqual(
            tickets.first().title,
            "New"
        )


class ServiceDeskViewTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="tester",
            password="password123"
        )

        self.client.login(
            username="tester",
            password="password123"
        )

        self.ticket = Ticket.objects.create(
            title="Example Ticket",
            description="Example Description",
            created_by=self.user
        )

    def test_dashboard(self):

        response = self.client.get(
            reverse("service_desk:dashboard")
        )

        self.assertEqual(response.status_code, 200)

    def test_ticket_list(self):

        response = self.client.get(
            reverse("service_desk:ticket_list")
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            self.ticket.title
        )

    def test_ticket_detail(self):

        response = self.client.get(
            reverse(
                "service_desk:ticket_detail",
                args=[self.ticket.pk]
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            self.ticket.title
        )

    def test_ticket_create_page(self):

        response = self.client.get(
            reverse("service_desk:ticket_create")
        )

        self.assertEqual(response.status_code, 200)