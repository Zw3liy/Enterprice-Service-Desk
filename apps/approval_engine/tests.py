from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.approval_engine.models import ApprovalPolicy
from apps.approval_engine.services import ApprovalEngine
from apps.service_desk.models import Company, Department, Status
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class ApprovalEngineTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="AprCo", slug="apr-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(username="req1", password="pass12345")
        self.approver = User.objects.create_user(
            username="apr1", password="pass12345", is_staff=True
        )

    def test_policy_and_ticket_approval(self):
        policies = ApprovalEngine.ensure_default_policies(self.company)
        self.assertGreaterEqual(len(policies), 1)
        self.assertTrue(ApprovalPolicy.objects.filter(company=self.company).exists())
        ticket = TicketService.create_ticket(
            title="Need approval",
            company=self.company,
            actor=self.user,
            run_ai=False,
        )
        req = ApprovalEngine.request_ticket_approval(
            ticket, self.approver, requested_by=self.user, reason="Please approve"
        )
        self.assertEqual(req.approver_id, self.approver.pk)
        pending = ApprovalEngine.pending_for(self.approver)
        self.assertEqual(pending.count(), 1)
