"""SOC security incidents and playbook runs."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, Ticket, TimeStampedModel


class SecurityIncident(TimeStampedModel):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class State(models.TextChoices):
        NEW = "new", "New"
        TRIAGE = "triage", "Triage"
        CONTAINMENT = "containment", "Containment"
        ERADICATION = "eradication", "Eradication"
        RECOVERY = "recovery", "Recovery"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="security_incidents"
    )
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_incident",
    )
    title = models.CharField(max_length=240)
    summary = models.TextField(blank=True)
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.MEDIUM
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.NEW)
    category = models.CharField(max_length=80, blank=True, default="general")
    source = models.CharField(max_length=80, blank=True, default="manual")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_incidents",
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    contained_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    iocs = models.JSONField(default=list, blank=True)
    mitre_tactics = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return self.title


class SOCPlaybook(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="soc_playbooks"
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=60)
    description = models.TextField(blank=True)
    steps = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PlaybookRun(TimeStampedModel):
    class State(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    security_incident = models.ForeignKey(
        SecurityIncident, on_delete=models.CASCADE, related_name="playbook_runs"
    )
    playbook = models.ForeignKey(
        SOCPlaybook, on_delete=models.CASCADE, related_name="runs"
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.RUNNING)
    current_step = models.PositiveIntegerField(default=0)
    log = models.JSONField(default=list, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
