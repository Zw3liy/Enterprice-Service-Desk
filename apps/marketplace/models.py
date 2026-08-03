"""Integration marketplace catalog and install records."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class MarketplaceApp(TimeStampedModel):
    class Category(models.TextChoices):
        COMMUNICATION = "communication", "Communication"
        MONITORING = "monitoring", "Monitoring"
        IDENTITY = "identity", "Identity"
        DEVOPS = "devops", "DevOps"
        PRODUCTIVITY = "productivity", "Productivity"
        SECURITY = "security", "Security"
        OTHER = "other", "Other"

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    vendor = models.CharField(max_length=120, blank=True)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.OTHER
    )
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, blank=True, default="fa-puzzle-piece")
    version = models.CharField(max_length=40, default="1.0.0")
    config_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema describing required configuration keys.",
    )
    webhook_events = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    documentation_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class InstalledApp(TimeStampedModel):
    class State(models.TextChoices):
        INSTALLED = "installed", "Installed"
        DISABLED = "disabled", "Disabled"
        ERROR = "error", "Error"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="installed_apps"
    )
    app = models.ForeignKey(
        MarketplaceApp, on_delete=models.CASCADE, related_name="installations"
    )
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.INSTALLED
    )
    config = models.JSONField(default=dict, blank=True)
    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ("company", "app")
        ordering = ["app__name"]

    def __str__(self) -> str:
        return f"{self.company.slug}:{self.app.slug}"
