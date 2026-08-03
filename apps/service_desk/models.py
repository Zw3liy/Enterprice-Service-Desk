<<<<<<< HEAD
from django.conf import settings
from django.db import models
from django.urls import reverse
=======
"""
Enterprise Service Desk — core domain models (ITIL-aligned).

Clean Architecture / DDD aggregate roots:
  Company (tenant boundary)
  Ticket  (case management aggregate)
  Asset   (CMDB configuration item)
  KnowledgeArticle
  SLA / Escalation
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
>>>>>>> 43f299f104a26a02e672f1ae2b81774211179472
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


<<<<<<< HEAD
class Ticket(models.Model):

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("ON_HOLD", "On Hold"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    CATEGORY_CHOICES = [
        ("INCIDENT", "Incident"),
        ("SERVICE_REQUEST", "Service Request"),
        ("PROBLEM", "Problem"),
        ("CHANGE", "Change"),
    ]

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )

    subject = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="INCIDENT",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_tickets",
        on_delete=models.CASCADE,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tickets",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
=======
# ---------------------------------------------------------------------------
# Mixins / base
# ---------------------------------------------------------------------------


class TimeStampedModel(models.Model):
    """Abstract audit timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(models.Model):
    """Optional UUID identity for external integrations."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Tenant / organization
# ---------------------------------------------------------------------------


class Company(TimeStampedModel):
    """Multi-tenant organization boundary."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    is_active = models.BooleanField(default=True)
    timezone = models.CharField(max_length=64, default="Africa/Johannesburg")
    primary_email = models.EmailField(blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)


class Department(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=40)
    email = models.EmailField(blank=True)
    ticket_counter = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="sd_department_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"


class Contact(TimeStampedModel):
    """End-user / requester identity (may link to auth user)."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_desk_contact",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    vip = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["company__name", "last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "email"],
                name="sd_contact_company_email_unique",
            )
        ]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class AgentProfile(TimeStampedModel):
    """Technician / agent extension of Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_profile",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="agents", null=True, blank=True
    )
    display_name = models.CharField(max_length=160, blank=True)
    is_available = models.BooleanField(default=True)
    max_open_tickets = models.PositiveIntegerField(default=25)
    skills = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["display_name", "user__username"]

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()


# ---------------------------------------------------------------------------
# Classification / routing
# ---------------------------------------------------------------------------


class Category(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="ticket_categories")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=60)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="sd_category_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Priority(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="priorities")
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=40)
    rank = models.PositiveSmallIntegerField(default=100)
    colour = models.CharField(max_length=7, default="#6c757d")
    impact = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    urgency = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "rank", "name"]
        verbose_name_plural = "priorities"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="sd_priority_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Status(TimeStampedModel):
    class CategoryChoice(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        PENDING = "pending", "Pending"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="ticket_statuses")
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=40)
    rank = models.PositiveSmallIntegerField(default=100)
    category = models.CharField(
        max_length=20, choices=CategoryChoice.choices, default=CategoryChoice.NEW
    )
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    colour = models.CharField(max_length=7, default="#0d6efd")

    class Meta:
        ordering = ["company__name", "rank", "name"]
        verbose_name_plural = "statuses"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="sd_status_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Queue(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="queues")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queues",
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=40)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="service_desk_queues",
    )

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="sd_queue_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class RequestType(TimeStampedModel):
    """Configurable service request catalog item."""

    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="request_types"
    )
    name = models.CharField(max_length=150)
    code = models.SlugField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_priority = models.ForeignKey(
        Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    default_queue = models.ForeignKey(
        Queue, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    sla = models.ForeignKey(
        "SLA", on_delete=models.SET_NULL, null=True, blank=True, related_name="request_types"
    )

    class Meta:
        ordering = ["department__name", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.code:
            self.code = slugify(self.name)[:60]
        super().save(*args, **kwargs)


class CustomField(TimeStampedModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Text area"
        NUMBER = "number", "Number"
        DROPDOWN = "dropdown", "Dropdown"
        MULTISELECT = "multiselect", "Multi-select"
        DATE = "date", "Date"
        DATETIME = "datetime", "Date & time"
        BOOLEAN = "boolean", "Boolean"
        EMAIL = "email", "Email"
        URL = "url", "URL"

    request_type = models.ForeignKey(
        RequestType, on_delete=models.CASCADE, related_name="custom_fields"
    )
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=160, blank=True)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    validation_regex = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.label or self.name

    def clean(self) -> None:
        if self.field_type in {self.FieldType.DROPDOWN, self.FieldType.MULTISELECT}:
            if not self.options:
                raise ValidationError({"options": "Dropdown fields require at least one option."})


# ---------------------------------------------------------------------------
# SLA / Escalation
# ---------------------------------------------------------------------------


class SLA(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="slas")
    name = models.CharField(max_length=160)
    priority = models.ForeignKey(
        Priority,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slas",
    )
    response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()
    business_hours_only = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["company__name", "name"]
        verbose_name = "SLA"
        verbose_name_plural = "SLAs"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="sd_sla_company_name_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class EscalationPolicy(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="escalation_policies"
    )
    name = models.CharField(max_length=160)
    sla = models.ForeignKey(
        SLA, on_delete=models.CASCADE, related_name="escalation_policies"
    )
    level = models.PositiveSmallIntegerField(default=1)
    trigger_after_percent = models.PositiveSmallIntegerField(
        default=80,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Escalate when elapsed time reaches this % of SLA target.",
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="escalation_policies"
    )
    target_queue = models.ForeignKey(
        Queue, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sla", "level"]
        verbose_name_plural = "escalation policies"

    def __str__(self) -> str:
        return f"{self.name} (L{self.level})"


class Escalation(TimeStampedModel):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="escalations")
    sla = models.ForeignKey(
        SLA, on_delete=models.SET_NULL, null=True, blank=True, related_name="escalations"
    )
    policy = models.ForeignKey(
        EscalationPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalations",
    )
    level = models.PositiveSmallIntegerField(default=1)
    reason = models.TextField()
    state = models.CharField(max_length=20, choices=State.choices, default=State.OPEN)
    escalated_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-escalated_at"]

    def __str__(self) -> str:
        return f"Escalation L{self.level} on {self.ticket_id}"


# ---------------------------------------------------------------------------
# CMDB / Assets
# ---------------------------------------------------------------------------


class Asset(TimeStampedModel, UUIDPrimaryKeyModel):
    class AssetType(models.TextChoices):
        COMPUTER = "computer", "Computer"
        SERVER = "server", "Server"
        NETWORK_DEVICE = "network_device", "Network device"
        PRINTER = "printer", "Printer"
        MOBILE = "mobile", "Mobile device"
        SOFTWARE = "software", "Software"
        LICENSE = "license", "License"
        CONTRACT = "contract", "Contract"
        CLOUD = "cloud", "Cloud resource"
        OTHER = "other", "Other"

    class LifecycleState(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        IN_STOCK = "in_stock", "In stock"
        IN_USE = "in_use", "In use"
        MAINTENANCE = "maintenance", "Maintenance"
        RETIRED = "retired", "Retired"
        DISPOSED = "disposed", "Disposed"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets")
    name = models.CharField(max_length=200)
    asset_tag = models.CharField(max_length=100)
    asset_type = models.CharField(
        max_length=30, choices=AssetType.choices, default=AssetType.OTHER
    )
    lifecycle_state = models.CharField(
        max_length=20, choices=LifecycleState.choices, default=LifecycleState.IN_USE
    )
    serial_number = models.CharField(max_length=160, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=200, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="ZAR")
    owner = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["company__name", "asset_tag"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "asset_tag"],
                name="sd_asset_company_tag_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.asset_tag} — {self.name}"


class AssetRelationship(TimeStampedModel):
    class RelationType(models.TextChoices):
        DEPENDS_ON = "depends_on", "Depends on"
        RUNS_ON = "runs_on", "Runs on"
        CONNECTED_TO = "connected_to", "Connected to"
        HOSTED_ON = "hosted_on", "Hosted on"
        OWNED_BY = "owned_by", "Owned by"
        RELATED = "related", "Related"

    source = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="outbound_relations")
    target = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="inbound_relations")
    relation_type = models.CharField(
        max_length=30, choices=RelationType.choices, default=RelationType.RELATED
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "target", "relation_type"],
                name="sd_asset_relation_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.source} {self.relation_type} {self.target}"


# ---------------------------------------------------------------------------
# Ticket aggregate
# ---------------------------------------------------------------------------


class Ticket(TimeStampedModel, UUIDPrimaryKeyModel):
    class TicketType(models.TextChoices):
        INCIDENT = "incident", "Incident"
        SERVICE_REQUEST = "service_request", "Service request"
        PROBLEM = "problem", "Problem"
        CHANGE = "change", "Change"
        QUESTION = "question", "Question"
        TASK = "task", "Task"

    class Channel(models.TextChoices):
        PORTAL = "portal", "Portal"
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        CHAT = "chat", "Chat"
        API = "api", "API"
        MONITORING = "monitoring", "Monitoring"
        WALK_IN = "walk_in", "Walk-in"

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    ticket_number = models.CharField(max_length=50, unique=True, blank=True)
    ticket_type = models.CharField(
        max_length=30, choices=TicketType.choices, default=TicketType.INCIDENT
    )
    channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.PORTAL
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="tickets",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="tickets",
        null=True,
        blank=True,
    )
    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    priority = models.ForeignKey(
        Priority,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    queue = models.ForeignKey(
        Queue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    sla = models.ForeignKey(
        SLA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    # Requester: prefer Contact; fall back to auth user for simplicity
    requester = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    requester_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_tickets",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    assets = models.ManyToManyField(Asset, blank=True, related_name="tickets")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    related_tickets = models.ManyToManyField(
        "self", blank=True, symmetrical=True
    )

    custom_field_values = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    impact = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    urgency = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # SLA clocks
    response_due_at = models.DateTimeField(null=True, blank=True)
    resolution_due_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    sla_response_breached = models.BooleanField(default=False)
    sla_resolution_breached = models.BooleanField(default=False)

    is_major_incident = models.BooleanField(default=False)
    sentiment_score = models.FloatField(null=True, blank=True)
    ai_category_suggestion = models.CharField(max_length=160, blank=True)
    ai_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="sd_ticket_co_status"),
            models.Index(fields=["queue", "status"], name="sd_ticket_qu_status"),
            models.Index(fields=["assignee", "status"], name="sd_ticket_as_status"),
            models.Index(fields=["ticket_type", "created_at"], name="sd_ticket_type_created"),
            models.Index(fields=["resolution_due_at"], name="sd_ticket_res_due"),
        ]
        permissions = [
            ("can_assign_ticket", "Can assign tickets"),
            ("can_escalate_ticket", "Can escalate tickets"),
            ("can_view_internal_comments", "Can view internal comments"),
            ("can_manage_sla", "Can manage SLA definitions"),
        ]

    def __str__(self) -> str:
        return self.ticket_number or self.title

    # ------------------------------------------------------------------
    # Domain behaviour
    # ------------------------------------------------------------------

    def generate_ticket_number(self) -> str:
        """Allocate a unique department-scoped ticket number under row lock."""
        year = timezone.now().year
        if self.department_id:
            department = (
                Department.objects.select_for_update().get(pk=self.department_id)
            )
            department.ticket_counter += 1
            department.save(update_fields=["ticket_counter", "updated_at"])
            code = (department.code or "TKT").upper()[:10]
            return f"{code}-{year}-{department.ticket_counter:05d}"

        # Fallback global sequence using ticket pk after insert is not available;
        # use company counter stored in settings JSON.
        prefix = "ESD"
        if self.company_id:
            company = Company.objects.select_for_update().get(pk=self.company_id)
            counter = int(company.settings.get("ticket_counter", 0)) + 1
            company.settings["ticket_counter"] = counter
            company.save(update_fields=["settings", "updated_at"])
            prefix = (company.slug or "ESD").upper()[:8]
            return f"{prefix}-{year}-{counter:05d}"

        return f"ESD-{year}-{uuid.uuid4().hex[:8].upper()}"

    def apply_sla_deadlines(self) -> None:
        """Compute response/resolution due timestamps from linked SLA."""
        if not self.sla_id:
            return
        sla = self.sla
        if sla is None:
            return
        base = self.created_at or timezone.now()
        self.response_due_at = base + timezone.timedelta(minutes=sla.response_minutes)
        self.resolution_due_at = base + timezone.timedelta(minutes=sla.resolution_minutes)

    def mark_first_response(self, when: Optional[timezone.datetime] = None) -> None:
        if self.first_response_at:
            return
        self.first_response_at = when or timezone.now()
        if self.response_due_at and self.first_response_at > self.response_due_at:
            self.sla_response_breached = True

    def mark_resolved(self, when: Optional[timezone.datetime] = None) -> None:
        self.resolved_at = when or timezone.now()
        if self.resolution_due_at and self.resolved_at > self.resolution_due_at:
            self.sla_resolution_breached = True

    def mark_closed(self, when: Optional[timezone.datetime] = None) -> None:
        if not self.resolved_at:
            self.mark_resolved(when)
        self.closed_at = when or timezone.now()

    def is_open(self) -> bool:
        if self.status_id and self.status:
            return not self.status.is_terminal
        return self.closed_at is None

    def save(self, *args: Any, **kwargs: Any) -> None:
        creating = self.pk is None
        if not self.ticket_number:
            with transaction.atomic():
                self.ticket_number = self.generate_ticket_number()
                if creating and self.sla_id and not self.response_due_at:
                    # created_at not set yet — apply after first save
                    super().save(*args, **kwargs)
                    # refresh created_at
                    type(self).objects.filter(pk=self.pk).update()
                    self.refresh_from_db(fields=["created_at"])
                    self.apply_sla_deadlines()
                    super().save(
                        update_fields=[
                            "response_due_at",
                            "resolution_due_at",
                            "updated_at",
                        ]
                    )
                    return
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)


class TicketComment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_comments",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment on {self.ticket_id}"


class TicketAttachment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    comment = models.ForeignKey(
        TicketComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    file = models.FileField(upload_to="ticketing/attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_name


class TicketAssignment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="assignments")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_assignments_made",
    )
    queue = models.ForeignKey(
        Queue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-assigned_at"]

    def __str__(self) -> str:
        return f"Assignment of {self.ticket_id}"


class WorkLog(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="work_logs")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_logs",
    )
    description = models.TextField()
    minutes_spent = models.PositiveIntegerField()
    performed_at = models.DateTimeField(default=timezone.now)
    is_billable = models.BooleanField(default=False)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return f"{self.minutes_spent}m on {self.ticket_id}"


class TicketWatcher(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="watchers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watched_tickets"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "user"], name="sd_ticket_watcher_unique"
            )
        ]


class AuditLog(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_desk_audit_logs",
    )
    action = models.CharField(max_length=120)
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"], name="sd_audit_co_created"),
            models.Index(fields=["action", "created_at"], name="sd_audit_action_created"),
        ]

    def __str__(self) -> str:
        return f"{self.action} @ {self.created_at}"


class CustomerFeedback(TimeStampedModel):
    ticket = models.OneToOneField(
        Ticket, on_delete=models.CASCADE, related_name="feedback"
    )
    submitted_by = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_submissions",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"CSAT {self.rating} for {self.ticket_id}"


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------


class KnowledgeArticle(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="knowledge_articles"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_articles",
    )
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=260)
    summary = models.TextField(blank=True)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
    is_internal = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_articles",
    )
    view_count = models.PositiveIntegerField(default=0)
    helpful_yes = models.PositiveIntegerField(default=0)
    helpful_no = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    related_tickets = models.ManyToManyField(
        Ticket, blank=True, related_name="knowledge_articles"
    )

    class Meta:
        ordering = ["-published_at", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "slug"],
                name="sd_article_company_slug_unique",
            )
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.title)[:260]
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class Notification(TimeStampedModel):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-app"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WEBHOOK = "webhook", "Webhook"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        READ = "read", "Read"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_desk_notifications",
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"], name="sd_notif_recipient_status"),
        ]

    def __str__(self) -> str:
        return self.subject

    def mark_read(self) -> None:
        self.status = self.Status.READ
        self.read_at = timezone.now()
        self.save(update_fields=["status", "read_at", "updated_at"])


class WebhookEndpoint(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="webhooks")
    name = models.CharField(max_length=120)
    url = models.URLField()
    secret = models.CharField(max_length=128, blank=True)
    events = models.JSONField(
        default=list,
        blank=True,
        help_text="Event names this endpoint subscribes to, e.g. ticket.created",
    )
    is_active = models.BooleanField(default=True)
    headers = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AutomationRule(TimeStampedModel):
    """Event-driven automation (assignment, status, notifications)."""

    class Trigger(models.TextChoices):
        TICKET_CREATED = "ticket.created", "Ticket created"
        TICKET_UPDATED = "ticket.updated", "Ticket updated"
        TICKET_ASSIGNED = "ticket.assigned", "Ticket assigned"
        COMMENT_ADDED = "comment.added", "Comment added"
        SLA_WARNING = "sla.warning", "SLA warning"
        SLA_BREACHED = "sla.breached", "SLA breached"
        STATUS_CHANGED = "status.changed", "Status changed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="automation_rules"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    trigger = models.CharField(max_length=40, choices=Trigger.choices)
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON conditions evaluated against the event payload.",
    )
    actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of actions: assign, set_status, notify, add_tag, webhook.",
    )
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=100)
    stop_processing = models.BooleanField(
        default=False,
        help_text="If true, no further rules run after this one matches.",
    )

    class Meta:
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return self.name


class ApprovalRequest(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="approvals")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_requests_made",
>>>>>>> 43f299f104a26a02e672f1ae2b81774211179472
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    reason = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

<<<<<<< HEAD
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):

        if not self.ticket_number:

            year = timezone.now().year

            last = (
                Ticket.objects
                .filter(ticket_number__startswith=f"INC-{year}")
                .count()
            )

            self.ticket_number = (
                f"INC-{year}-{last + 1:05d}"
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):

        return reverse(
            "ticket_detail",
            kwargs={"pk": self.pk},
        )
=======
    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Approval {self.state} for {self.ticket_id}"



>>>>>>> 43f299f104a26a02e672f1ae2b81774211179472
