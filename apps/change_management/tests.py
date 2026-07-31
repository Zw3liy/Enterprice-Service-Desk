from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.change_management.models import ChangeRequest
from apps.change_management.services import ChangeService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class ChangeServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="ChgCo", slug="chg-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="chgagent", password="pass12345", is_staff=True
        )
        self.approver = User.objects.create_user(
            username="cab1", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )

    def test_lifecycle(self):
        ticket = ChangeService.create_change(
            title="Upgrade edge firewall",
            company=self.company,
            department=self.dept,
            status=self.status,
            change_type=ChangeRequest.ChangeType.NORMAL,
            risk=ChangeRequest.Risk.HIGH,
            justification="Security patch",
            actor=self.user,
            run_ai=False,
        )
        change = ticket.change_request
        self.assertEqual(change.state, ChangeRequest.State.DRAFT)
        ChangeService.submit(ticket, actor=self.user)
        ChangeService.request_cab_approval(ticket, approver=self.approver, requested_by=self.user)
        ChangeService.decide(ticket, approver=self.approver, approved=True, comment="OK")
        ticket.change_request.refresh_from_db()
        self.assertEqual(ticket.change_request.state, ChangeRequest.State.APPROVED)
        ChangeService.complete(ticket, success=True, actor=self.user)
        ticket.change_request.refresh_from_db()
        self.assertEqual(ticket.change_request.state, ChangeRequest.State.COMPLETED)


class ChangeUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="ChgUI", slug="chg-ui")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(
            username="chgui", password="pass12345", is_staff=True
        )
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )
        self.client = Client()
        self.client.login(username="chgui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_list(self):
        ChangeService.create_change(
            title="Patch cluster",
            company=self.company,
            department=self.dept,
            status=self.status,
            actor=self.user,
            run_ai=False,
        )
        res = self.client.get(reverse("changes:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Patch cluster")