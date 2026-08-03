"""Reusable form definitions beyond request-type custom fields."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, RequestType, TimeStampedModel


class FormDefinition(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="form_definitions"
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=60)
    description = models.TextField(blank=True)
    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_definitions",
    )
    schema = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered field definitions: name, label, type, required, options.",
    )
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class FormSubmission(TimeStampedModel):
    form = models.ForeignKey(
        FormDefinition, on_delete=models.CASCADE, related_name="submissions"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="form_submissions"
    )
    values = models.JSONField(default=dict)
    submitted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )
    ticket = models.ForeignKey(
        "service_desk.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    class Meta:
        ordering = ["-created_at"]
