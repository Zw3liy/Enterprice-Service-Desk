"""Compliance controls, assessments, and evidence."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class ControlFramework(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="control_frameworks"
    )
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=40)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Control(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_ASSESSED = "not_assessed", "Not assessed"
        COMPLIANT = "compliant", "Compliant"
        PARTIAL = "partial", "Partially compliant"
        NON_COMPLIANT = "non_compliant", "Non-compliant"

    framework = models.ForeignKey(
        ControlFramework, on_delete=models.CASCADE, related_name="controls"
    )
    control_id = models.CharField(max_length=40)
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOT_ASSESSED
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_controls",
    )
    last_reviewed_at = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("framework", "control_id")
        ordering = ["control_id"]

    def __str__(self) -> str:
        return f"{self.control_id} — {self.title}"


class ComplianceEvidence(TimeStampedModel):
    control = models.ForeignKey(Control, on_delete=models.CASCADE, related_name="evidence")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    collected_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-collected_at"]

    def __str__(self) -> str:
        return self.title
