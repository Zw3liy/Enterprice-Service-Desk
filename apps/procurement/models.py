"""Purchase requests and purchase orders."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel
from apps.vendor_management.models import Vendor


class PurchaseRequest(TimeStampedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ORDERED = "ordered", "Ordered"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="purchase_requests"
    )
    number = models.CharField(max_length=40, unique=True, blank=True)
    title = models.CharField(max_length=200)
    justification = models.TextField(blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_requests",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_approvals",
    )
    needed_by = models.DateField(null=True, blank=True)
    total_estimate = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="ZAR")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.number or self.title

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"PR-{self.pk:07d}"
            super().save(update_fields=["number"])


class PurchaseRequestLine(TimeStampedModel):
    request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    sku = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["id"]

    @property
    def line_total(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price


class PurchaseOrder(TimeStampedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIALLY_RECEIVED = "partial", "Partially received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="purchase_orders"
    )
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    number = models.CharField(max_length=40, unique=True, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    currency = models.CharField(max_length=3, default="ZAR")
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    ordered_at = models.DateTimeField(null=True, blank=True)
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
        return self.number or f"PO-{self.pk}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"PO-{self.pk:07d}"
            super().save(update_fields=["number"])
