from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.incident_management.services import IncidentService
from apps.problem_management.models import ProblemRecord
from apps.problem_management.services import ProblemService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class ProblemServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PrbCo", slug="prb-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="prbagent", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )

    def test_create_link_root_cause(self):
        problem = ProblemService.create_problem(
            title="Recurring VPN drops",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        self.assertTrue(hasattr(problem, "problem_record"))
        incident = IncidentService.create_incident(
            title="VPN drop today",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        ProblemService.link_incident(problem, incident)
        record = ProblemService.set_root_cause(
            problem,
            root_cause="Faulty firewall firmware",
            workaround="Restart tunnel hourly",
            actor=self.user,
        )
        self.assertEqual(record.state, ProblemRecord.State.KNOWN_ERROR)
        self.assertEqual(record.related_incidents.count(), 1)


class ProblemUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PrbUI", slug="prb-ui")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="prbui", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )
        self.client = Client()
        self.client.login(username="prbui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_list(self):
        ProblemService.create_problem(
            title="Disk thrashing",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        res = self.client.get(reverse("problems:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Disk thrashing")