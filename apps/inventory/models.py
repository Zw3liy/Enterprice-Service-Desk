"""Stock items, warehouses, and stock movements."""

from __future__ import annotations

from django.conf import settings
from django.db import models, transaction

from apps.service_desk.models import Company, TimeStampedModel


class Warehouse(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="warehouses"
    )
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=160)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StockItem(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="stock_items"
    )
    sku = models.CharField(max_length=80)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, default="ea")
    reorder_level = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "sku")
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"


class StockLevel(TimeStampedModel):
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="levels"
    )
    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="levels")
    quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = ("warehouse", "item")

    def __str__(self) -> str:
        return f"{self.item.sku}@{self.warehouse.code}={self.quantity}"


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        ISSUE = "issue", "Issue"
        ADJUSTMENT = "adjustment", "Adjustment"
        TRANSFER = "transfer", "Transfer"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="stock_movements"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="movements"
    )
    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(help_text="Signed quantity; issues negative.")
    reference = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
