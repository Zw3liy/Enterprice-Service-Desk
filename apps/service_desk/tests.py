"""Unit and integration tests for Enterprise Service Desk."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.service_desk.models import (
    Asset,
    AuditLog,
    Category,
    Company,
    Contact,
    CustomerFeedback,
    Department,
    KnowledgeArticle,
    Priority,
    Queue,
    SLA,
    Status,
    Ticket,
    TicketAssignment,
    TicketComment,
    WorkLog,
)
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.services.assignment_service import AssignmentService
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.services.sla_service import SLAService
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class BaseESDTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Acme Holdings", slug="acme-holdings"
        )
        self.department = Department.objects.create(
            company=self.company, name="Information Technology", code="it"
        )
        self.admin = User.objects.create_user(
            username="admin", password="pass12345", is_staff=True, is_superuser=True
        )
        self.agent = User.objects.create_user(
            username="agent1", password="pass12345", is_staff=True
        )
        self.requester = Contact.objects.create(
            company=self.company,
            first_name="Ava",
            last_name="Mokoena",
            email="ava@example.com",
            user=self.admin,
        )
        self.queue = Queue.objects.create(
            company=self.company,
            department=self.department,
            name="Service Desk",
            code="service-desk",
        )
        self.queue.members.add(self.agent)
        self.category = Category.objects.create(
            company=self.company, name="Connectivity", code="network"
        )
        self.priority = Priority.objects.create(
            company=self.company, name="High", code="high", rank=20, colour="#ea580c"
        )
        self.status_new = Status.objects.create(
            company=self.company,
            name="New",
            code="new",
            rank=10,
            category=Status.CategoryChoice.NEW,
        )
        self.status_open = Status.objects.create(
            company=self.company,
            name="Open",
            code="open",
            rank=20,
            category=Status.CategoryChoice.IN_PROGRESS,
        )
        self.status_resolved = Status.objects.create(
            company=self.company,
            name="Resolved",
            code="resolved",
            rank=50,
            category=Status.CategoryChoice.RESOLVED,
            is_terminal=False,
        )
        self.status_closed = Status.objects.create(
            company=self.company,
            name="Closed",
            code="closed",
            rank=60,
            category=Status.CategoryChoice.CLOSED,
            is_terminal=True,
        )
        self.sla = SLA.objects.create(
            company=self.company,
            name="High priority standard",
            priority=self.priority,
            response_minutes=30,
            resolution_minutes=240,
        )
        self.client = Client()
        self.client.login(username="admin", password="pass12345")
        session = self.client.session
        session["company_id"] = self.company.pk
        session.save()


class TicketingRouteTests(BaseESDTestCase):
    def test_ticket_list_uses_the_ticketing_namespace(self):
        ticket = TicketService.create_ticket(
            title="Network connectivity issue",
            company=self.company,
            department=self.department,
            status=self.status_new,
            priority=self.priority,
            actor=self.admin,
            run_ai=False,
        )
        response = self.client.get(reverse("ticketing:ticket_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ticket.title)
        self.assertContains(response, "Enterprise")

    def test_dashboard_renders_metrics(self):
        TicketService.create_ticket(
            title="Dashboard seed",
            company=self.company,
            department=self.department,
            status=self.status_open,
            actor=self.admin,
            run_ai=False,
        )
        response = self.client.get(reverse("service_desk:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open tickets")


class EnterpriseDomainModelTests(BaseESDTestCase):
    def test_ticket_preserves_enterprise_relationships(self):
        asset = Asset.objects.create(
            company=self.company,
            name="Branch router",
            asset_tag="RTR-001",
            asset_type=Asset.AssetType.NETWORK_DEVICE,
            owner=self.requester,
        )
        ticket = TicketService.create_ticket(
            title="Branch cannot reach the internet",
            description="WAN connection is unavailable.",
            company=self.company,
            department=self.department,
            category=self.category,
            priority=self.priority,
            status=self.status_new,
            queue=self.queue,
            sla=self.sla,
            requester=self.requester,
            requester_user=self.admin,
            assets=[asset],
            actor=self.admin,
            run_ai=False,
        )
        self.assertTrue(ticket.ticket_number)
        self.assertIn("IT-", ticket.ticket_number)
        self.assertEqual(ticket.assets.count(), 1)
        self.assertEqual(ticket.company_id, self.company.pk)
        self.assertIsNotNone(ticket.response_due_at)
        self.assertIsNotNone(ticket.resolution_due_at)

    def test_unique_ticket_numbers(self):
        t1 = TicketService.create_ticket(
            title="One",
            company=self.company,
            department=self.department,
            actor=self.admin,
            run_ai=False,
        )
        t2 = TicketService.create_ticket(
            title="Two",
            company=self.company,
            department=self.department,
            actor=self.admin,
            run_ai=False,
        )
        self.assertNotEqual(t1.ticket_number, t2.ticket_number)


class TicketServiceTests(BaseESDTestCase):
    def test_comment_and_worklog(self):
        ticket = TicketService.create_ticket(
            title="Need help",
            company=self.company,
            department=self.department,
            status=self.status_new,
            actor=self.admin,
            run_ai=False,
        )
        comment = TicketService.add_comment(
            ticket, body="Looking into this", author=self.agent
        )
        self.assertIsInstance(comment, TicketComment)
        log = TicketService.add_work_log(
            ticket, description="Diagnostics", minutes_spent=15, author=self.agent
        )
        self.assertIsInstance(log, WorkLog)
        self.assertEqual(ticket.comments.count(), 1)

    def test_assignment(self):
        ticket = TicketService.create_ticket(
            title="Assign me",
            company=self.company,
            department=self.department,
            queue=self.queue,
            status=self.status_new,
            actor=self.admin,
            run_ai=False,
        )
        AssignmentService.assign(
            ticket, assignee=self.agent, queue=self.queue, assigned_by=self.admin
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.assignee_id, self.agent.pk)
        self.assertTrue(TicketAssignment.objects.filter(ticket=ticket).exists())

    def test_resolve_status_sets_timestamp(self):
        ticket = TicketService.create_ticket(
            title="Resolve me",
            company=self.company,
            department=self.department,
            status=self.status_open,
            actor=self.admin,
            run_ai=False,
        )
        TicketService.update_ticket(
            ticket, actor=self.admin, status=self.status_resolved
        )
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.resolved_at)


class AIServiceTests(BaseESDTestCase):
    def test_classify_network_outage(self):
        result = AIService.classify_text(
            "Production VPN outage — entire office cannot work"
        )
        self.assertEqual(result["category"], "network")
        self.assertIn(result["priority_hint"], {"critical", "high"})

    def test_enrich_sets_summary(self):
        ticket = TicketService.create_ticket(
            title="Email issue",
            description="Outlook crashes when opening calendar. Thanks for helping.",
            company=self.company,
            department=self.department,
            actor=self.admin,
            run_ai=True,
        )
        ticket.refresh_from_db()
        self.assertTrue(ticket.ai_summary)


class DashboardServiceTests(BaseESDTestCase):
    def test_summary_counts(self):
        TicketService.create_ticket(
            title="A",
            company=self.company,
            department=self.department,
            status=self.status_open,
            actor=self.admin,
            run_ai=False,
        )
        summary = DashboardService.summary(company=self.company, user=self.admin)
        self.assertGreaterEqual(summary["total_tickets"], 1)
        self.assertGreaterEqual(summary["open_tickets"], 1)


class SLAServiceTests(BaseESDTestCase):
    def test_attach_default_sla(self):
        ticket = Ticket(
            title="SLA",
            company=self.company,
            department=self.department,
            priority=self.priority,
        )
        SLAService.attach_default_sla(ticket)
        self.assertEqual(ticket.sla_id, self.sla.pk)


class KnowledgeTests(BaseESDTestCase):
    def test_knowledge_list(self):
        KnowledgeArticle.objects.create(
            company=self.company,
            title="Reset password",
            slug="reset-password",
            body="Steps...",
            is_published=True,
        )
        response = self.client.get(reverse("service_desk:knowledge_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset password")


class APITests(BaseESDTestCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        token = Token.objects.create(user=self.admin)
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_and_list_tickets(self):
        payload = {
            "title": "API created ticket",
            "description": "Created via REST",
            "company": self.company.pk,
            "department": self.department.pk,
            "priority": self.priority.pk,
            "status": self.status_new.pk,
            "queue": self.queue.pk,
        }
        res = self.api.post("/api/v1/tickets/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIn("ticket_number", res.data)
        res_list = self.api.get("/api/v1/tickets/")
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(res_list.data["count"], 1)

    def test_dashboard_api(self):
        res = self.api.get("/api/v1/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("open_tickets", res.data)

    def test_ai_classify_api(self):
        res = self.api.post(
            "/api/v1/ai/classify/",
            {"text": "Cannot login — password locked after MFA"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["category"], "access")


class HealthTests(TestCase):
    def test_healthz(self):
        c = Client()
        res = c.get("/healthz/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")
