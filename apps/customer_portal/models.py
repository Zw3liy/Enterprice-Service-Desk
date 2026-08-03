"""Customer portal preferences and service catalog requests."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class PortalProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portal_profile",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="portal_profiles"
    )
    display_name = models.CharField(max_length=160, blank=True)
    department_name = models.CharField(max_length=120, blank=True)
    notify_email = models.BooleanField(default=True)
    notify_in_app = models.BooleanField(default=True)
    preferred_language = models.CharField(max_length=10, default="en")

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()


class PortalAnnouncement(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="portal_announcements"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["priority", "-created_at"]

    def __str__(self) -> str:
        return self.title