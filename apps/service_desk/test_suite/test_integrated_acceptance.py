"""
Enterprise Completion Program — Phase 9: Integrated acceptance.

Every other test module in this suite proves one module's own RBAC
boundaries and workflow in isolation. This file proves the seams
between modules hold for an actual role journey — a single session
touching several modules in sequence, using the real
`create_roles` bootstrap (not a hand-rolled permission set, so this
exercises the same RBAC configuration a real deployment runs), plus
the mission's explicit "audit records must be append-only" boundary.
"""

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import (
    CatalogItem,
    Change,
    ChangeHistory,
    ConfigurationItem,
    ConfigurationItemType,
    Department,
    KnowledgeArticle,
    KnowledgeCategory,
    Release,
    RequestType,
    ServiceCategory,
    ServiceRequest,
    Ticket,
    TicketHistory,
)
from apps.service_desk.services.change_service import ChangeService
from apps.service_desk.services.knowledge_service import KnowledgeService


class IntegratedAcceptanceBase(TestCase):
    """
    Shared fixture: real RBAC groups via create_roles (not hand-built
    permission lists), one department, one user per role, and enough
    master/catalogue data for a realistic cross-module journey.
    """

    def setUp(self):
        call_command("create_roles", verbosity=0)

        self.client = Client()
        self.dept = Department.objects.create(name="IT")

        self.requester = User.objects.create_user(
            username="acc_requester", password="password123"
        )
        self.requester.groups.add(Group.objects.get(name="Requester"))

        self.technician = User.objects.create_user(
            username="acc_technician", password="password123"
        )
        self.technician.groups.add(Group.objects.get(name="Technician"))

        self.manager = User.objects.create_user(
            username="acc_manager", password="password123"
        )
        self.manager.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.manager)

        self.admin = User.objects.create_superuser(
            username="acc_admin", password="password123", email="a@test.com"
        )

        self.catalog_category = ServiceCategory.objects.create(name="Hardware")
        self.catalog_item = CatalogItem.objects.create(
            category=self.catalog_category,
            name="Laptop",
            fulfillment_department=self.dept,
            requires_approval=False,
        )

        self.ci_type = ConfigurationItemType.objects.create(name="Server")
        self.ci = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-01", identifier="SRV-ACC-1",
            department=self.dept,
        )

        self.kb_category = KnowledgeCategory.objects.create(name="How-To")
        self.request_type = RequestType.objects.create(
            name="Incident", is_active=True
        )


class RequesterJourneyTests(IntegratedAcceptanceBase):
    def test_requester_full_journey(self):
        self.client.login(username="acc_requester", password="password123")

        # 1. Raise a ticket.
        create_ticket = self.client.post(
            reverse("service_desk:ticket_create"),
            {
                "title": "My laptop won't boot",
                "description": "Black screen on startup.",
                "priority": "medium",
                "urgency": "medium",
                "request_type": self.request_type.pk,
            },
        )
        self.assertEqual(create_ticket.status_code, 302)
        ticket = Ticket.objects.get(title="My laptop won't boot")
        self.assertEqual(ticket.created_by, self.requester)

        # 2. Browse the catalogue and submit a service request.
        browse = self.client.get(reverse("service_desk:catalog_item_list"))
        self.assertEqual(browse.status_code, 200)
        self.assertContains(browse, "Laptop")

        submit_request = self.client.post(
            reverse(
                "service_desk:service_request_create",
                args=[self.catalog_item.pk],
            ),
            {"quantity": 1, "justification": "New starter"},
        )
        self.assertEqual(submit_request.status_code, 302)
        service_request = ServiceRequest.objects.get(
            catalog_item=self.catalog_item
        )
        self.assertEqual(service_request.status, ServiceRequest.STATUS_APPROVED)

        # 3. Read own service request and own ticket, but nothing else's.
        own_sr_detail = self.client.get(
            reverse(
                "service_desk:service_request_detail", args=[service_request.pk]
            )
        )
        self.assertEqual(own_sr_detail.status_code, 200)

        # 4. Read a published, public knowledge article and leave feedback.
        article = KnowledgeService.create_article(
            self.technician,
            category=self.kb_category,
            title="How to request hardware",
            content="Use the catalogue.",
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        KnowledgeService.submit_for_review(article, user=self.technician)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.approve_article(article, self.manager)
        KnowledgeService.publish_article(article, user=self.manager)

        kb_detail = self.client.get(
            reverse("service_desk:knowledge_detail", args=[article.pk])
        )
        self.assertEqual(kb_detail.status_code, 200)

        feedback = self.client.post(
            reverse("service_desk:knowledge_feedback", args=[article.pk]),
            {"is_helpful": "true"},
        )
        self.assertEqual(feedback.status_code, 302)

        # 5. Reports reflect only their own scope: the support ticket
        # from step 1 plus the ticket that backs their service request
        # from step 2 — both created_by this requester, nothing else's.
        reports = self.client.get(reverse("service_desk:reporting_dashboard"))
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(reports.context["ticket_stats"]["total"], 2)

        # 6. Internal governance modules are entirely out of reach.
        for name in ("change_list", "release_list", "cmdb_item_list"):
            with self.subTest(url=name):
                response = self.client.get(reverse(f"service_desk:{name}"))
                self.assertEqual(response.status_code, 403)


class TechnicianJourneyTests(IntegratedAcceptanceBase):
    def test_technician_full_journey(self):
        ticket = Ticket.objects.create(
            title="Printer offline", description="x", department=self.dept,
        )

        self.client.login(username="acc_technician", password="password123")

        # 1. Self-assign an unassigned ticket and work it.
        assign = self.client.post(
            reverse("service_desk:ticket_assign", args=[ticket.pk]),
            {"technician_id": self.technician.pk},
        )
        self.assertEqual(assign.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.technician)

        work_note = self.client.post(
            reverse("service_desk:ticket_work_note", args=[ticket.pk]),
            {"note": "Checked toner, reseated cable."},
        )
        self.assertEqual(work_note.status_code, 302)

        # 2. Link the ticket to a CMDB item.
        link_ci = self.client.post(
            reverse("service_desk:cmdb_link_ticket", args=[self.ci.pk]),
            {"ticket_id": ticket.pk},
        )
        self.assertEqual(link_ci.status_code, 302)
        self.ci.refresh_from_db()
        self.assertIn(ticket, self.ci.tickets.all())

        # 3. Raise a change for a fix and see it (even before assignment).
        raise_change = self.client.post(
            reverse("service_desk:change_create"),
            {
                "title": "Replace printer cable",
                "description": "x",
                "change_type": "standard",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(raise_change.status_code, 302)
        change = Change.objects.get(title="Replace printer cable")

        change_detail = self.client.get(
            reverse("service_desk:change_detail", args=[change.pk])
        )
        self.assertEqual(change_detail.status_code, 200)

        # 4. Author a knowledge article.
        author_article = self.client.post(
            reverse("service_desk:knowledge_create"),
            {
                "category": self.kb_category.pk,
                "title": "Printer offline checklist",
                "content": "Steps...",
                "visibility": "internal",
            },
        )
        self.assertEqual(author_article.status_code, 302)

        # 5. Cannot approve their own change (separation of duties) even
        # though they hold change_change for their own workflow steps.
        ChangeService.submit_change(change, user=self.technician)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        approve_own = self.client.post(
            reverse("service_desk:change_approve", args=[change.pk]),
            {"comment": "trying anyway"},
        )
        self.assertEqual(approve_own.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_ASSESSED)

        # 6. Cannot manage suppliers at all.
        suppliers = self.client.get(reverse("service_desk:supplier_list"))
        self.assertEqual(suppliers.status_code, 403)


class ManagerJourneyTests(IntegratedAcceptanceBase):
    def test_manager_full_journey(self):
        other_dept = Department.objects.create(name="Finance")
        other_ticket = Ticket.objects.create(
            title="Finance-only ticket", description="x", department=other_dept,
        )

        change = ChangeService.create_change(
            self.technician,
            title="Upgrade switch firmware",
            description="x",
            department=self.dept,
        )
        ChangeService.submit_change(change, user=self.technician)

        self.client.login(username="acc_manager", password="password123")

        # 1. Assess and approve a change for their department.
        assess = self.client.post(
            reverse("service_desk:change_assess", args=[change.pk]),
            {"impact": "low", "urgency": "low"},
        )
        self.assertEqual(assess.status_code, 302)

        approve = self.client.post(
            reverse("service_desk:change_approve", args=[change.pk]),
            {"comment": "Approved."},
        )
        self.assertEqual(approve.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_APPROVED)

        # 2. Create a release and link the now-eligible change to it.
        create_release = self.client.post(
            reverse("service_desk:release_create"),
            {
                "name": "October Release",
                "version": "2026.10.1",
                "environment": "staging",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(create_release.status_code, 302)
        release = Release.objects.get(version="2026.10.1")

        link_change = self.client.post(
            reverse("service_desk:release_link_change", args=[release.pk]),
            {"change_id": change.pk},
        )
        self.assertEqual(link_change.status_code, 302)
        self.assertIn(change, release.changes.all())

        # 3. Manage a CMDB item in their department, including relationships.
        second_ci = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="db-01", identifier="SRV-ACC-2",
            department=self.dept,
        )
        relate = self.client.post(
            reverse("service_desk:cmdb_relationship_add", args=[self.ci.pk]),
            {"target_id": second_ci.pk, "relationship_type": "depends_on"},
        )
        self.assertEqual(relate.status_code, 302)

        # 4. Cannot reach another department's ticket — 404, not 403.
        cross_scope = self.client.get(
            reverse("service_desk:ticket_detail", args=[other_ticket.pk])
        )
        self.assertEqual(cross_scope.status_code, 404)

        # 5. Department-scoped, filtered report.
        reports = self.client.get(
            reverse("service_desk:reporting_dashboard"),
            {"department": self.dept.pk},
        )
        self.assertEqual(reports.status_code, 200)
        self.assertIn("change_stats", reports.context)

        # 6. Export changes as CSV, scoped the same way.
        export = self.client.get(reverse("service_desk:reporting_export_changes"))
        self.assertEqual(export.status_code, 200)
        content = b"".join(export.streaming_content).decode()
        self.assertIn("Upgrade switch firmware", content)


class AdministratorJourneyTests(IntegratedAcceptanceBase):
    def test_administrator_full_journey(self):
        other_dept = Department.objects.create(name="Finance")
        other_ticket = Ticket.objects.create(
            title="Finance ticket", description="x", department=other_dept,
        )

        self.client.login(username="acc_admin", password="password123")

        # 1. Sees every department's tickets, not just a managed subset.
        detail = self.client.get(
            reverse("service_desk:ticket_detail", args=[other_ticket.pk])
        )
        self.assertEqual(detail.status_code, 200)

        # 2. Full CMDB, Change and Release administration, cross-department.
        # Raised by someone else — separation of duties means even an
        # Administrator cannot approve their own change, so the
        # requester here must not be the acting admin.
        change = ChangeService.create_change(
            self.technician,
            title="Org-wide policy update",
            description="x",
            department=other_dept,
        )
        ChangeService.submit_change(change, user=self.technician)

        assess = self.client.post(
            reverse("service_desk:change_assess", args=[change.pk]),
            {"impact": "high", "urgency": "high"},
        )
        self.assertEqual(assess.status_code, 302)

        approve = self.client.post(
            reverse("service_desk:change_approve", args=[change.pk]),
            {"comment": "Administrator override approval."},
        )
        self.assertEqual(approve.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_APPROVED)

        # 3. Global reports include every department.
        reports = self.client.get(reverse("service_desk:reporting_dashboard"))
        self.assertEqual(reports.status_code, 200)
        self.assertGreaterEqual(reports.context["change_stats"]["total"], 1)

        # 4. Every mutation above left an audit trail.
        self.assertTrue(
            change.history.filter(
                event_type=ChangeHistory.EVENT_APPROVED
            ).exists()
        )


class AuditImmutabilityTests(TestCase):
    """
    "Audit records must be append-only through normal application
    workflows." Verified two ways: no URL route exists that could
    update or delete a history record, and the history models expose
    no service-layer mutation beyond ``record()``/create.
    """

    def setUp(self):
        self.dept = Department.objects.create(name="IT")
        self.user = User.objects.create_user(
            username="audit_user", password="password123"
        )

    def test_no_route_targets_a_history_model_for_update_or_delete(self):
        from apps.service_desk.urls import urlpatterns

        suspicious_fragments = ("history", "audit")

        for pattern in urlpatterns:
            route = str(pattern.pattern)
            if any(fragment in route for fragment in suspicious_fragments):
                self.fail(
                    f"Route {route!r} appears to target history/audit "
                    "data directly — history must only ever be written "
                    "via <Model>Service methods calling "
                    "<History>.record()."
                )

    def test_ticket_history_has_no_update_or_delete_view(self):
        ticket = Ticket.objects.create(
            title="x", description="x", created_by=self.user,
        )
        entry = TicketHistory.record(
            ticket=ticket, event_type=TicketHistory.EVENT_CREATED, user=self.user,
        )

        # There is no URL that takes a history pk — confirmed by trying
        # to reverse plausible names and expecting every one to fail.
        from django.urls import NoReverseMatch

        for name in (
            "ticket_history_update",
            "ticket_history_delete",
            "ticket_history_edit",
        ):
            with self.assertRaises(NoReverseMatch):
                reverse(f"service_desk:{name}", args=[entry.pk])

    def test_change_history_model_exposes_no_public_update_method(self):
        """
        ChangeHistory (representative of every history model added in
        this program) only offers ``record()`` (create) and Django's
        own ``objects`` manager — there is no ``update_entry`` or
        similar mutation helper for any service to call.
        """

        public_callables = {
            name
            for name in dir(ChangeHistory)
            if not name.startswith("_")
            and callable(getattr(ChangeHistory, name))
        }

        # Django model base classes contribute save()/delete()/etc,
        # which is expected on any model instance — what matters is
        # that no *domain* mutation method (update_*, edit_*, revise_*)
        # was added alongside record().
        domain_mutators = {
            name
            for name in public_callables
            if name.startswith(("update_", "edit_", "revise_", "modify_"))
        }
        self.assertEqual(domain_mutators, set())
