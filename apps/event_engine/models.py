"""Persisted domain events for audit/replay."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class DomainEvent(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="domain_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=120, db_index=True)
    aggregate_type = models.CharField(max_length=80, blank=True)
    aggregate_id = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.aggregate_id}"
