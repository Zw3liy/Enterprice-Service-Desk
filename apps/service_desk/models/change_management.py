from django.conf import settings
from django.db import models

from .ticket import Ticket


class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SCHEDULED = "scheduled", "Scheduled"
        IMPLEMENTED = "implemented", "Implemented"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Risk(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="change_requests",
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    risk = models.CharField(
        max_length=20,
        choices=Risk.choices,
        default=Risk.MEDIUM,
    )

    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_changes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["requester"]),
            models.Index(fields=["ticket"]),
        ]

    def __str__(self):
        return f"CHG-{self.pk}: {self.title}"


class CABDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DEFERRED = "deferred", "Deferred"

    change = models.ForeignKey(
        ChangeRequest,
        on_delete=models.CASCADE,
        related_name="cab_decisions",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cab_decisions",
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
    )

    notes = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.change} - {self.get_decision_display()}"


class ChangeTask(models.Model):
    change = models.ForeignKey(
        ChangeRequest,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    name = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name