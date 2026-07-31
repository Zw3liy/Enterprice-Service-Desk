"""ITIL Incident records extending the core Ticket aggregate."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, Ticket, TimeStampedModel


class MajorIncident(TimeStampedModel):
    """Major incident bridge with bridge team and comms tracking."""

    class Severity(models.TextChoices):
        SEV1 = "sev1", "Severity 1"
        SEV2 = "sev2", "Severity 2"
        SEV3 = "sev3", "Severity 3"

    ticket = models.OneToOneField(
        Ticket, on_delete=models.CASCADE, related_name="major_incident_record"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="major_incidents"
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.SEV1
    )
    bridge_channel = models.CharField(max_length=255, blank=True)
    commander = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commanded_incidents",
    )
    customer_impact = models.TextField(blank=True)
    status_page_url = models.URLField(blank=True)
    declared_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    postmortem_required = models.BooleanField(default=True)
    postmortem_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-declared_at"]

    def __str__(self) -> str:
        return f"MI-{self.ticket.ticket_number}"


class IncidentTimelineEvent(TimeStampedModel):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="incident_timeline"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=60, default="update")
    message = models.TextField()
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.message[:40]}"