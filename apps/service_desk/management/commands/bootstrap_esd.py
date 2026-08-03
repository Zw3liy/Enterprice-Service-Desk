"""Bootstrap default tenant, catalogs, admin user, and sample data."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.service_desk.models import (
    Asset,
    AutomationRule,
    Category,
    Company,
    Contact,
    Department,
    KnowledgeArticle,
    Priority,
    Queue,
    RequestType,
    CustomField,
    SLA,
    Status,
    AgentProfile,
)
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class Command(BaseCommand):
    help = "Bootstrap Enterprise Service Desk with default company, catalogs, and admin."

    def add_arguments(self, parser):
        parser.add_argument("--admin-user", default="admin")
        parser.add_argument("--admin-password", default="admin123!")
        parser.add_argument("--admin-email", default="admin@example.com")
        parser.add_argument("--company-name", default="Default Organization")
        parser.add_argument("--company-slug", default="default")
        parser.add_argument("--with-demo", action="store_true", help="Create demo tickets")

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            slug=options["company_slug"],
            defaults={
                "name": options["company_name"],
                "primary_email": "servicedesk@example.com",
                "timezone": "Africa/Johannesburg",
            },
        )
        self.stdout.write(f"Company: {company.name}")

        dept, _ = Department.objects.get_or_create(
            company=company,
            code="it",
            defaults={"name": "Information Technology", "email": "it@example.com"},
        )

        statuses = [
            ("new", "New", Status.CategoryChoice.NEW, 10, False, "#0d6efd"),
            ("open", "Open", Status.CategoryChoice.IN_PROGRESS, 20, False, "#2563eb"),
            ("in_progress", "In Progress", Status.CategoryChoice.IN_PROGRESS, 30, False, "#7c3aed"),
            ("pending", "Pending Customer", Status.CategoryChoice.PENDING, 40, False, "#d97706"),
            ("resolved", "Resolved", Status.CategoryChoice.RESOLVED, 50, False, "#059669"),
            ("closed", "Closed", Status.CategoryChoice.CLOSED, 60, True, "#6b7280"),
            ("cancelled", "Cancelled", Status.CategoryChoice.CANCELLED, 70, True, "#9ca3af"),
        ]
        status_map = {}
        for code, name, cat, rank, terminal, colour in statuses:
            obj, _ = Status.objects.update_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "category": cat,
                    "rank": rank,
                    "is_terminal": terminal,
                    "colour": colour,
                    "is_active": True,
                },
            )
            status_map[code] = obj

        priorities = [
            ("critical", "Critical", 10, "#dc2626", 1, 1),
            ("high", "High", 20, "#ea580c", 2, 2),
            ("medium", "Medium", 30, "#ca8a04", 3, 3),
            ("low", "Low", 40, "#65a30d", 4, 4),
        ]
        priority_map = {}
        for code, name, rank, colour, impact, urgency in priorities:
            obj, _ = Priority.objects.update_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "rank": rank,
                    "colour": colour,
                    "impact": impact,
                    "urgency": urgency,
                    "is_active": True,
                },
            )
            priority_map[code] = obj

        slas = {}
        for code, resp, reso in [
            ("critical", 15, 240),
            ("high", 30, 480),
            ("medium", 120, 1440),
            ("low", 480, 4320),
        ]:
            sla, _ = SLA.objects.update_or_create(
                company=company,
                name=f"{code.title()} priority standard",
                defaults={
                    "priority": priority_map[code],
                    "response_minutes": resp,
                    "resolution_minutes": reso,
                    "is_active": True,
                },
            )
            slas[code] = sla

        queue, _ = Queue.objects.get_or_create(
            company=company,
            code="service-desk",
            defaults={
                "name": "Service Desk",
                "department": dept,
                "description": "Tier-1 service desk queue",
            },
        )

        categories = [
            ("network", "Network"),
            ("email", "Email & Collaboration"),
            ("hardware", "Hardware"),
            ("access", "Access & Identity"),
            ("software", "Software"),
            ("telephony", "Telephony"),
        ]
        for code, name in categories:
            Category.objects.get_or_create(
                company=company, code=code, defaults={"name": name, "is_active": True}
            )

        rt, _ = RequestType.objects.get_or_create(
            department=dept,
            code="incident-general",
            defaults={
                "name": "General Incident",
                "description": "Catch-all IT incident",
                "default_priority": priority_map["medium"],
                "default_queue": queue,
                "sla": slas["medium"],
            },
        )
        CustomField.objects.get_or_create(
            request_type=rt,
            name="affected_service",
            defaults={
                "label": "Affected service",
                "field_type": CustomField.FieldType.TEXT,
                "is_required": False,
                "sort_order": 1,
            },
        )
        CustomField.objects.get_or_create(
            request_type=rt,
            name="business_impact",
            defaults={
                "label": "Business impact",
                "field_type": CustomField.FieldType.DROPDOWN,
                "options": ["Single user", "Team", "Department", "Organization"],
                "is_required": True,
                "sort_order": 2,
            },
        )

        admin, created = User.objects.get_or_create(
            username=options["admin_user"],
            defaults={
                "email": options["admin_email"],
                "is_staff": True,
                "is_superuser": True,
                "first_name": "System",
                "last_name": "Administrator",
            },
        )
        if created or options.get("admin_password"):
            admin.set_password(options["admin_password"])
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        AgentProfile.objects.update_or_create(
            user=admin,
            defaults={
                "company": company,
                "display_name": "Service Desk Admin",
                "is_available": True,
            },
        )
        queue.members.add(admin)

        Contact.objects.get_or_create(
            company=company,
            email=options["admin_email"],
            defaults={
                "first_name": "System",
                "last_name": "Administrator",
                "user": admin,
            },
        )

        Asset.objects.get_or_create(
            company=company,
            asset_tag="SRV-001",
            defaults={
                "name": "Primary Application Server",
                "asset_type": Asset.AssetType.SERVER,
                "lifecycle_state": Asset.LifecycleState.IN_USE,
                "location": "DC-Cape Town",
                "department": dept,
                "manufacturer": "Dell",
                "model_name": "PowerEdge R750",
            },
        )

        KnowledgeArticle.objects.get_or_create(
            company=company,
            slug="reset-password-self-service",
            defaults={
                "title": "How to reset your password",
                "summary": "Self-service password reset steps for Microsoft 365.",
                "body": (
                    "1. Go to https://passwordreset.microsoftonline.com\n"
                    "2. Enter your work email address.\n"
                    "3. Complete MFA verification.\n"
                    "4. Choose a new strong password.\n"
                    "5. Sign in again on all devices."
                ),
                "is_published": True,
                "published_at": timezone.now(),
                "author": admin,
                "tags": ["password", "access", "m365"],
            },
        )
        KnowledgeArticle.objects.get_or_create(
            company=company,
            slug="vpn-connection-troubleshooting",
            defaults={
                "title": "VPN connection troubleshooting",
                "summary": "Resolve common VPN connectivity issues.",
                "body": (
                    "Check network connectivity, ensure the VPN client is updated, "
                    "verify credentials, and confirm MFA prompts are approved. "
                    "If the tunnel establishes but apps fail, flush DNS and retry."
                ),
                "is_published": True,
                "published_at": timezone.now(),
                "author": admin,
                "tags": ["vpn", "network"],
            },
        )

        AutomationRule.objects.get_or_create(
            company=company,
            name="Auto-assign new incidents",
            defaults={
                "trigger": AutomationRule.Trigger.TICKET_CREATED,
                "conditions": {"ticket_type": "incident"},
                "actions": [{"type": "auto_assign"}, {"type": "add_tag", "tag": "auto-routed"}],
                "priority": 10,
                "is_active": True,
            },
        )

        # Billing plans + default subscription
        try:
            from apps.billing.services import BillingService

            BillingService.seed_plans()
            BillingService.subscribe(
                company, "professional", seats=10, trial_days=30, actor=admin
            )
            self.stdout.write("Billing plans seeded; professional trial attached.")
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"Billing bootstrap skipped: {exc}"))

        # RBAC groups
        try:
            from apps.rbac.services import RBACService

            RBACService.ensure_groups()
            RBACService.ensure_role_definitions(company)
            RBACService.assign_role(admin, "admin", company=company, assigned_by=admin)
            self.stdout.write("RBAC groups ensured.")
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"RBAC bootstrap skipped: {exc}"))

        try:
            from apps.multi_tenant.models import TenantSettings

            TenantSettings.objects.get_or_create(company=company)
            self.stdout.write("Tenant settings ensured.")
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"Tenant bootstrap skipped: {exc}"))

        try:
            from apps.approval_engine.services import ApprovalEngine

            ApprovalEngine.ensure_default_policies(company)
            self.stdout.write("Approval policies ensured.")
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"Approval bootstrap skipped: {exc}"))

        try:
            from apps.marketplace.services import MarketplaceService

            MarketplaceService.seed_catalog()
            self.stdout.write("Marketplace catalog seeded.")
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"Marketplace bootstrap skipped: {exc}"))

        # CMDB classes
        try:
            from apps.cmdb.services import CMDBService

            CMDBService.ensure_default_classes(company)
            CMDBService.upsert_ci(
                company,
                name="Primary Application Server",
                ci_id="SRV-001",
                ci_class_code="server",
            )
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"CMDB bootstrap skipped: {exc}"))

        if options["with_demo"]:
            TicketService.create_ticket(
                title="Production VPN outage affecting Cape Town office",
                description=(
                    "Users cannot connect to VPN. Entire branch is offline from internal apps. "
                    "This is urgent and blocking payroll processing."
                ),
                company=company,
                department=dept,
                request_type=rt,
                priority=priority_map["critical"],
                queue=queue,
                status=status_map["new"],
                ticket_type="incident",
                channel="portal",
                requester_user=admin,
                actor=admin,
                auto_assign=True,
                custom_field_values={"business_impact": "Organization"},
            )
            TicketService.create_ticket(
                title="Outlook keeps prompting for password",
                description="Please help, Outlook on my laptop asks for password every hour.",
                company=company,
                department=dept,
                request_type=rt,
                priority=priority_map["medium"],
                queue=queue,
                status=status_map["open"],
                ticket_type="incident",
                channel="email",
                requester_user=admin,
                actor=admin,
                custom_field_values={"business_impact": "Single user", "affected_service": "Email"},
            )
            self.stdout.write(self.style.SUCCESS("Demo tickets created."))

        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))
        self.stdout.write(
            f"Login: {options['admin_user']} / {options['admin_password']}"
        )
