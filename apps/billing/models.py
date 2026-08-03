"""SaaS billing, plans, subscriptions, and usage metering."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.service_desk.models import Company, TimeStampedModel


class Plan(TimeStampedModel):
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STARTER)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    price_yearly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")
    max_agents = models.PositiveIntegerField(default=5)
    max_tickets_per_month = models.PositiveIntegerField(default=500)
    max_assets = models.PositiveIntegerField(default=100)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self) -> str:
        return self.name


class Subscription(TimeStampedModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TRIALING
    )
    seats = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    billing_email = models.EmailField(blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    external_customer_id = models.CharField(max_length=120, blank=True)
    external_subscription_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.company} → {self.plan}"

    @property
    def is_usable(self) -> bool:
        return self.status in {self.Status.TRIALING, self.Status.ACTIVE}


class UsageRecord(TimeStampedModel):
    class Metric(models.TextChoices):
        TICKETS = "tickets", "Tickets"
        AGENTS = "agents", "Agents"
        ASSETS = "assets", "Assets"
        API_CALLS = "api_calls", "API calls"
        STORAGE_MB = "storage_mb", "Storage MB"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="usage_records"
    )
    metric = models.CharField(max_length=30, choices=Metric.choices)
    quantity = models.PositiveIntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["company", "metric", "period_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.company_id}:{self.metric}={self.quantity}"


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        VOID = "void", "Void"
        UNCOLLECTIBLE = "uncollectible", "Uncollectible"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="invoices"
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    line_items = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.number