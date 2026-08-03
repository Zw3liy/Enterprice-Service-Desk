from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.service_desk.models import Company, Department, Status
from apps.soc_center.models import SecurityIncident
from apps.soc_center.services import SOCService

User = get_user_model()


class SOCServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="SocCo", slug="soc-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(
            username="soc1", password="pass12345", is_staff=True
        )

    def test_open_and_playbook(self):
        SOCService.ensure_default_playbooks(self.company)
        si = SOCService.open_incident(
            self.company,
            title="Suspicious PowerShell on endpoint",
            severity=SecurityIncident.Severity.HIGH,
            category="malware",
            iocs=["evil.example.com"],
            actor=self.user,
        )
        self.assertIsNotNone(si.ticket_id)
        playbook = self.company.soc_playbooks.first()
        run = SOCService.start_playbook(si, playbook, user=self.user)
        SOCService.advance_playbook(run, note="host isolated", user=self.user)
        run.refresh_from_db()
        self.assertEqual(run.current_step, 1)
