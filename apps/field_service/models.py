"""Field service work orders for on-site technicians."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, Ticket, TimeStampedModel


class WorkOrder(TimeStampedModel):
    class State(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        DISPATCHED = "dispatched", "Dispatched"
        ON_SITE = "on_site", "On site"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="work_orders")
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="work_orders"
    )
    number = models.CharField(max_length=40, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_orders",
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.SCHEDULED)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_start", "-created_at"]

    def __str__(self) -> str:
        return self.number or self.title

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"WO-{self.pk:07d}"
            super().save(update_fields=["number"])
