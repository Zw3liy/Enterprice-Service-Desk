"""Monitoring alerts that can open incidents."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, Ticket, TimeStampedModel


class MonitoringAlert(TimeStampedModel):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class State(models.TextChoices):
        OPEN = "open", "Open"
        ACKED = "acked", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        SUPPRESSED = "suppressed", "Suppressed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="monitoring_alerts"
    )
    source = models.CharField(max_length=80, default="generic")
    external_id = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.WARNING
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.OPEN)
    host = models.CharField(max_length=200, blank=True)
    service = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_alerts",
    )
    fired_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fired_at"]
        indexes = [
            models.Index(fields=["company", "state", "severity"]),
            models.Index(fields=["source", "external_id"]),
        ]

    def __str__(self) -> str:
        return self.title
