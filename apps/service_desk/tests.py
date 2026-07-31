from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import (
    Asset,
    AuditLog,
    Category,
    Company,
    Contact,
    CustomerFeedback,
    Department,
    Escalation,
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


class TicketingRouteTests(TestCase):
    def test_ticket_list_uses_the_ticketing_namespace(self):
        ticket = Ticket.objects.create(title="Network connectivity issue")

        response = self.client.get(reverse("ticketing:ticket_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ticket.title)
        self.assertContains(response, "Enterprise Service Desk")


class EnterpriseDomainModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Holdings", slug="acme-holdings")
        self.department = Department.objects.create(
            company=self.company, name="Information Technology", code="it"
        )
        self.requester = Contact.objects.create(
            company=self.company,
            first_name="Ava",
            last_name="Mokoena",
            email="ava@example.com",
        )
        self.queue = Queue.objects.create(
            company=self.company, department=self.department, name="Service Desk", code="service-desk"
        )
        self.category = Category.objects.create(
            company=self.company, name="Connectivity", code="connectivity"
        )
        self.priority = Priority.objects.create(
            company=self.company, name="High", code="high", rank=20
        )
        self.status = Status.objects.create(
            company=self.company, name="Open", code="open", rank=10
        )
        self.sla = SLA.objects.create(
            company=self.company,
            name="High priority standard",
            priority=self.priority,
            response_minutes=30,
            resolution_minutes=240,
        )

    def test_ticket_preserves_legacy_fields_and_accepts_enterprise_relationships(self):
        asset = Asset.objects.create(
            company=self.company,
            name="Branch router",
            asset_tag="RTR-001",
            asset_type=Asset.AssetType.NETWORK_DEVICE,
            owner=self.requester,
        )
        ticket = Ticket.objects.create(
            title="Branch cannot reach the internet",
            description="WAN connection is unavailable.",
            company=self.company,
            requester=self.requester,
            department=self.department,
            queue=self.queue,
            category=self.category,
            priority_definition=self.priority,
            status_definition=self.status,
            sla=self.sla,
        )
        ticket.assets.add(asset)

        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.priority, "medium")
        self.assertEqual(ticket.ticket_number, f"ESD-{ticket.pk:07d}")
        self.assertEqual(list(ticket.assets.all()), [asset])
        self.assertEqual(ticket.requester.display_name, "Ava Mokoena")

    def test_company_scoped_codes_are_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Queue.objects.create(
                company=self.company,
                name="Duplicate service desk",
                code="service-desk",
            )

        other_company = Company.objects.create(name="Other Holdings", slug="other-holdings")
        Queue.objects.create(company=other_company, name="Service Desk", code="service-desk")

    def test_operational_and_knowledge_records_attach_to_ticket_domain(self):
        ticket = Ticket.objects.create(title="VPN access request", company=self.company, requester=self.requester)
        assignment = TicketAssignment.objects.create(ticket=ticket, queue=self.queue)
        comment = TicketComment.objects.create(ticket=ticket, body="Access request received.")
        work_log = WorkLog.objects.create(ticket=ticket, description="Validated requester identity.", minutes_spent=15)
        escalation = Escalation.objects.create(ticket=ticket, sla=self.sla, reason="Response target breached.")
        audit = AuditLog.objects.create(company=self.company, ticket=ticket, action="ticket.created")
        article = KnowledgeArticle.objects.create(
            company=self.company,
            category=self.category,
            title="Connecting to the VPN",
            slug="connecting-to-the-vpn",
            body="Use the approved VPN client.",
        )
        feedback = CustomerFeedback.objects.create(ticket=ticket, submitted_by=self.requester, rating=5)

        self.assertEqual(ticket.assignments.get(), assignment)
        self.assertEqual(ticket.comments.get(), comment)
        self.assertEqual(ticket.work_logs.get(), work_log)
        self.assertEqual(ticket.escalations.get(), escalation)
        self.assertEqual(ticket.audit_logs.get(), audit)
        self.assertEqual(article.company, self.company)
        self.assertEqual(ticket.feedback, feedback)

    def test_ticket_detail_uses_the_ticketing_namespace(self):
        ticket = Ticket.objects.create(title="VPN access request")

        response = self.client.get(reverse("ticketing:ticket_detail", args=[ticket.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ticket.title)
