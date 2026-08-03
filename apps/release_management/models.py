"""ITIL Release & Deployment management."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.change_management.models import ChangeRequest
from apps.service_desk.models import Company, TimeStampedModel


class Release(TimeStampedModel):
    class State(models.TextChoices):
        PLANNED = "planned", "Planned"
        BUILD = "build", "Build"
        TEST = "test", "Test"
        READY = "ready", "Ready for deployment"
        DEPLOYING = "deploying", "Deploying"
        DEPLOYED = "deployed", "Deployed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="releases")
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PLANNED)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_releases",
    )
    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    changes = models.ManyToManyField(ChangeRequest, blank=True, related_name="releases")
    deployment_notes = models.TextField(blank=True)
    rollback_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-planned_start", "-created_at"]
        unique_together = ("company", "version")

    def __str__(self) -> str:
        return f"{self.name} ({self.version})"


class ReleaseTask(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"
        SKIPPED = "skipped", "Skipped"

    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_tasks",
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    sequence = models.PositiveIntegerField(default=10)
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self) -> str:
        return self.title
