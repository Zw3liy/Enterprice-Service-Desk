"""Multi-tenant domain and isolation metadata."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class TenantDomain(TimeStampedModel):
    """Custom domain / subdomain mapping for a tenant company."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="tenant_domains"
    )
    domain = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_primary", "domain"]

    def __str__(self) -> str:
        return self.domain


class TenantSettings(TimeStampedModel):
    """Per-tenant feature flags and branding."""

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="tenant_settings"
    )
    feature_flags = models.JSONField(default=dict, blank=True)
    branding = models.JSONField(default=dict, blank=True)
    data_residency = models.CharField(max_length=40, blank=True, default="ZA")
    max_users = models.PositiveIntegerField(default=100)
    allow_public_signup = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "tenant settings"

    def __str__(self) -> str:
        return f"Settings for {self.company}"
