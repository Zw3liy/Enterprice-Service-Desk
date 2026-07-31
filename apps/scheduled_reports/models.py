"""Scheduled report definitions and run history."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class ScheduledReport(TimeStampedModel):
    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    class ReportType(models.TextChoices):
        TICKET_CSV = "ticket_csv", "Tickets CSV"
        DASHBOARD_JSON = "dashboard_json", "Dashboard JSON"
        SLA_SUMMARY = "sla_summary", "SLA summary"
        VULN_SUMMARY = "vuln_summary", "Vulnerability summary"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="scheduled_reports"
    )
    name = models.CharField(max_length=160)
    report_type = models.CharField(
        max_length=40, choices=ReportType.choices, default=ReportType.TICKET_CSV
    )
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY
    )
    recipients = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ReportRun(TimeStampedModel):
    class State(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    report = models.ForeignKey(
        ScheduledReport, on_delete=models.CASCADE, related_name="runs"
    )
    state = models.CharField(max_length=20, choices=State.choices)
    row_count = models.PositiveIntegerField(default=0)
    artifact_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
