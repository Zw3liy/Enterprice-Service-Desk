from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.monitoring_engine.models import MonitoringAlert
from apps.monitoring_engine.services import MonitoringService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class MonitoringServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="MonCo", slug="mon-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(
            username="monagent", password="pass12345", is_staff=True
        )

    def test_ingest_opens_incident(self):
        alert = MonitoringService.ingest(
            self.company,
            title="CPU > 95% on app-01",
            severity=MonitoringAlert.Severity.CRITICAL,
            source="prometheus",
            external_id="alert-1",
            host="app-01",
            actor=self.user,
        )
        self.assertEqual(alert.state, MonitoringAlert.State.OPEN)
        self.assertIsNotNone(alert.ticket_id)
        # duplicate external id should not open second ticket while open
        alert2 = MonitoringService.ingest(
            self.company,
            title="CPU > 95% on app-01",
            severity=MonitoringAlert.Severity.CRITICAL,
            source="prometheus",
            external_id="alert-1",
            host="app-01",
            actor=self.user,
        )
        self.assertEqual(alert.pk, alert2.pk)


class MonitoringAPITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="MonAPI", slug="mon-api")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(
            username="monapi", password="pass12345", is_staff=True
        )
        self.api = APIClient()
        token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        s = self.api.session
        s["company_id"] = self.company.pk
        s.save()

    def test_ingest_api(self):
        res = self.api.post(
            "/monitoring/api/ingest/",
            {
                "title": "Disk full",
                "severity": "warning",
                "source": "zabbix",
                "host": "db-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIn("id", res.data)
