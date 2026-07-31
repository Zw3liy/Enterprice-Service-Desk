"""IT cost centers, budgets, and chargeback entries."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, Department, Ticket, TimeStampedModel


class CostCenter(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="cost_centers"
    )
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=160)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cost_centers",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Budget(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="budgets")
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.CASCADE, related_name="budgets"
    )
    fiscal_year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZAR")
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("cost_center", "fiscal_year")
        ordering = ["-fiscal_year", "cost_center__code"]

    def __str__(self) -> str:
        return f"{self.cost_center.code} FY{self.fiscal_year}"


class ChargebackEntry(TimeStampedModel):
    class Category(models.TextChoices):
        LABOR = "labor", "Labor"
        ASSET = "asset", "Asset"
        LICENSE = "license", "License"
        CLOUD = "cloud", "Cloud"
        VENDOR = "vendor", "Vendor"
        OTHER = "other", "Other"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="chargebacks"
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.CASCADE, related_name="chargebacks"
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.LABOR
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZAR")
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chargebacks",
    )
    posted_on = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-posted_on", "-created_at"]

    def __str__(self) -> str:
        return f"{self.description} ({self.amount})"
