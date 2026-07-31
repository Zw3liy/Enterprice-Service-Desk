from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.incident_management.models import MajorIncident
from apps.incident_management.services import IncidentService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class IncidentServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="IncCo", slug="inc-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="incagent", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )

    def test_create_and_declare_major(self):
        ticket = IncidentService.create_incident(
            title="Core switch down",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        self.assertEqual(ticket.ticket_type, "incident")
        mi = IncidentService.declare_major(
            ticket,
            severity=MajorIncident.Severity.SEV1,
            commander=self.user,
            customer_impact="All sites offline",
            actor=self.user,
        )
        self.assertTrue(ticket.is_major_incident)
        self.assertEqual(mi.severity, "sev1")
        self.assertEqual(IncidentService.timeline(ticket).count(), 1)


class IncidentUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="IncCo2", slug="inc-co-2")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="incui", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )
        self.client = Client()
        self.client.login(username="incui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_list_page(self):
        IncidentService.create_incident(
            title="Printer jam",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        res = self.client.get(reverse("incidents:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Printer jam")


class IncidentAPITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="IncAPI", slug="inc-api")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="incapi", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )
        self.api = APIClient()
        token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        # session company for tenancy
        self.ticket = IncidentService.create_incident(
            title="API incident",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )

    def test_list_api(self):
        res = self.api.get("/incidents/api/incidents/")
        self.assertEqual(res.status_code, 200)
