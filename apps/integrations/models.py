"""Integration connection registry."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class IntegrationConnection(TimeStampedModel):
    class Provider(models.TextChoices):
        EMAIL_IMAP = "email_imap", "Email IMAP"
        LDAP = "ldap", "LDAP / AD"
        M365 = "m365", "Microsoft 365"
        SLACK = "slack", "Slack"
        TEAMS = "teams", "Microsoft Teams"
        SMS = "sms", "SMS"
        CUSTOM = "custom", "Custom"

    class State(models.TextChoices):
        CONFIGURED = "configured", "Configured"
        ACTIVE = "active", "Active"
        ERROR = "error", "Error"
        DISABLED = "disabled", "Disabled"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="integration_connections"
    )
    provider = models.CharField(max_length=40, choices=Provider.choices)
    name = models.CharField(max_length=160)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.CONFIGURED
    )
    config = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["provider", "name"]
        unique_together = ("company", "provider", "name")

    def __str__(self) -> str:
        return f"{self.provider}:{self.name}"
