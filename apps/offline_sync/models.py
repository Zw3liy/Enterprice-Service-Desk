"""Client sync cursors and queued offline mutations."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class SyncCursor(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="sync_cursors"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sync_cursors",
    )
    device_id = models.CharField(max_length=120)
    last_pulled_at = models.DateTimeField(null=True, blank=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    cursor_token = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = ("user", "device_id")
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.device_id}"


class OfflineMutation(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"
        CONFLICT = "conflict", "Conflict"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="offline_mutations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offline_mutations",
    )
    device_id = models.CharField(max_length=120)
    client_mutation_id = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=64, blank=True)
    operation = models.CharField(max_length=40)
    payload = models.JSONField(default=dict)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    error_message = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "device_id", "client_mutation_id")
        ordering = ["created_at"]
