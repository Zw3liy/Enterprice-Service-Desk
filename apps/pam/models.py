"""Privileged access requests and sessions."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class PrivilegedAccount(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="privileged_accounts"
    )
    name = models.CharField(max_length=160)
    system = models.CharField(max_length=160, help_text="Target system, e.g. prod-db")
    username = models.CharField(max_length=120)
    environment = models.CharField(max_length=40, default="production")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["system", "name"]
        unique_together = ("company", "system", "username")

    def __str__(self) -> str:
        return f"{self.system}/{self.username}"


class AccessRequest(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="pam_requests"
    )
    account = models.ForeignKey(
        PrivilegedAccount, on_delete=models.CASCADE, related_name="requests"
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pam_requests",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pam_approvals",
    )
    justification = models.TextField()
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    requested_minutes = models.PositiveIntegerField(default=60)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PAM {self.account} for {self.requester}"


class PrivilegedSession(TimeStampedModel):
    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        EXPIRED = "expired", "Expired"

    access_request = models.ForeignKey(
        AccessRequest, on_delete=models.CASCADE, related_name="sessions"
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    session_token = models.CharField(max_length=64, unique=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    audit_trail = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]
