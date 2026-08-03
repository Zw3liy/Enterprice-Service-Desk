"""ITIL Change Management models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, Ticket, TimeStampedModel


class ChangeRequest(TimeStampedModel):
    class ChangeType(models.TextChoices):
        STANDARD = "standard", "Standard"
        NORMAL = "normal", "Normal"
        EMERGENCY = "emergency", "Emergency"

    class Risk(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        CAB_REVIEW = "cab_review", "CAB review"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        IMPLEMENTING = "implementing", "Implementing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"

    ticket = models.OneToOneField(
        Ticket, on_delete=models.CASCADE, related_name="change_request"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="change_requests"
    )
    change_type = models.CharField(
        max_length=20, choices=ChangeType.choices, default=ChangeType.NORMAL
    )
    risk = models.CharField(max_length=20, choices=Risk.choices, default=Risk.MEDIUM)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    justification = models.TextField(blank=True)
    implementation_plan = models.TextField(blank=True)
    rollback_plan = models.TextField(blank=True)
    test_plan = models.TextField(blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    cab_required = models.BooleanField(default=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_requests",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"CHG-{self.ticket.ticket_number}"


class CABMeeting(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="cab_meetings"
    )
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    chair = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chaired_cab_meetings",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="cab_memberships"
    )
    changes = models.ManyToManyField(
        ChangeRequest, blank=True, related_name="cab_meetings"
    )
    minutes = models.TextField(blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self) -> str:
        return self.title


class ChangeApproval(TimeStampedModel):
    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    change = models.ForeignKey(
        ChangeRequest, on_delete=models.CASCADE, related_name="approvals"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="change_approvals",
    )
    decision = models.CharField(
        max_length=20, choices=Decision.choices, default=Decision.PENDING
    )
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("change", "approver")

    def __str__(self) -> str:
        return f"{self.change_id}:{self.approver_id}:{self.decision}"