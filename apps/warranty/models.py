"""Asset warranty contracts."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Asset, Company, TimeStampedModel
from apps.vendor_management.models import Vendor


class WarrantyRecord(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        VOID = "void", "Void"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="warranties"
    )
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="warranties")
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranties",
    )
    provider_name = models.CharField(max_length=160, blank=True)
    contract_number = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    coverage = models.TextField(blank=True)
    support_phone = models.CharField(max_length=40, blank=True)
    support_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["end_date"]

    def __str__(self) -> str:
        return f"{self.asset.asset_tag} warranty → {self.end_date}"
