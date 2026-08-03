"""Vendor / supplier management."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class Vendor(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="vendors")
    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=60)
    website = models.URLField(blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=40, blank=True)
    account_manager = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    risk_rating = models.PositiveSmallIntegerField(default=3)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class VendorContract(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="contracts")
    title = models.CharField(max_length=200)
    contract_number = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    annual_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="ZAR")
    sla_summary = models.TextField(blank=True)
    auto_renew = models.BooleanField(default=False)
    document_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-end_date", "title"]

    def __str__(self) -> str:
        return self.title
