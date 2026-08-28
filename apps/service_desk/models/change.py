from django.conf import settings
from django.db import models
from django.utils import timezone

from .department import Department


class Change(models.Model):
    """
    A governed change record (ITIL Change Management).

    Requesters have no access to Change records at all — mirrors
    ADR-010, Decision 1's Problem Management precedent: Change
    Management is an internal IT governance process, not a
    requester-facing workflow (that is what Service Request
    Management, ADR-011, is for). See
    ``security.policies.get_change_queryset``.
    """

    TYPE_STANDARD = "standard"
    TYPE_NORMAL = "normal"
    TYPE_EMERGENCY = "emergency"

    TYPE_CHOICES = [
        (TYPE_STANDARD, "Standard"),
        (TYPE_NORMAL, "Normal"),
        (TYPE_EMERGENCY, "Emergency"),
    ]

    IMPACT_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    URGENCY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"

    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_MEDIUM, "Medium"),
        (RISK_HIGH, "High"),
        (RISK_CRITICAL, "Critical"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_ASSESSED = "assessed"
    STATUS_APPROVED = "approved"
    STATUS_SCHEDULED = "scheduled"
    STATUS_IMPLEMENTING = "implementing"
    STATUS_VALIDATION = "validation"
    STATUS_COMPLETED = "completed"
    STATUS_REJECTED = "rejected"
    STATUS_FAILED = "failed"
    STATUS_ROLLED_BACK = "rolled_back"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ASSESSED, "Assessed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IMPLEMENTING, "Implementing"),
        (STATUS_VALIDATION, "Validation"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_FAILED, "Failed"),
        (STATUS_ROLLED_BACK, "Rolled Back"),
    ]

    SCHEDULABLE_STATUSES = {STATUS_SCHEDULED, STATUS_IMPLEMENTING}

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    change_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_NORMAL,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changes",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_changes",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_changes",
        help_text="The implementer.",
    )

    impact = models.CharField(
        max_length=20,
        choices=IMPACT_CHOICES,
        null=True,
        blank=True,
    )

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        null=True,
        blank=True,
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_CHOICES,
        null=True,
        blank=True,
        help_text="Calculated from impact x urgency at assessment time.",
    )

    implementation_plan = models.TextField(
        blank=True,
        default="",
    )

    test_plan = models.TextField(
        blank=True,
        default="",
    )

    rollback_plan = models.TextField(
        blank=True,
        default="",
    )

    scheduled_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    scheduled_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Change"
        verbose_name_plural = "Changes"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["department"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["scheduled_start", "scheduled_end"]),
        ]

    def __str__(self):
        return f"[{self.pk}] {self.title}"

    @property
    def is_open(self):
        return self.status not in {
            self.STATUS_COMPLETED,
            self.STATUS_REJECTED,
            self.STATUS_ROLLED_BACK,
        }


class ChangeApproval(models.Model):
    """
    One CAB decision on a ``Change``.

    Append-only. Separation of duties (an approver may be neither the
    requester nor the assigned implementer) is enforced in
    ``ChangeService``, not here.
    """

    DECISION_APPROVED = "approved"
    DECISION_REJECTED = "rejected"

    DECISION_CHOICES = [
        (DECISION_APPROVED, "Approved"),
        (DECISION_REJECTED, "Rejected"),
    ]

    change = models.ForeignKey(
        Change,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_approvals",
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
    )

    comment = models.TextField(
        blank=True,
        default="",
    )

    decided_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-decided_at"]
        verbose_name = "Change Approval"
        verbose_name_plural = "Change Approvals"
        indexes = [
            models.Index(fields=["change", "decided_at"]),
        ]

    def __str__(self):
        return f"{self.change} - {self.get_decision_display()}"


class ChangeHistory(models.Model):
    """
    Immutable audit trail for change events.
    """

    EVENT_CREATED = "created"
    EVENT_SUBMITTED = "submitted"
    EVENT_ASSESSED = "assessed"
    EVENT_APPROVED = "approved"
    EVENT_REJECTED = "rejected"
    EVENT_SCHEDULED = "scheduled"
    EVENT_IMPLEMENTING = "implementing"
    EVENT_VALIDATION = "validation"
    EVENT_COMPLETED = "completed"
    EVENT_FAILED = "failed"
    EVENT_ROLLED_BACK = "rolled_back"
    EVENT_COMMENT = "comment"
    EVENT_ASSIGNED = "assigned"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_SUBMITTED, "Submitted"),
        (EVENT_ASSESSED, "Assessed"),
        (EVENT_APPROVED, "Approved"),
        (EVENT_REJECTED, "Rejected"),
        (EVENT_SCHEDULED, "Scheduled"),
        (EVENT_IMPLEMENTING, "Implementing"),
        (EVENT_VALIDATION, "Validation"),
        (EVENT_COMPLETED, "Completed"),
        (EVENT_FAILED, "Failed"),
        (EVENT_ROLLED_BACK, "Rolled Back"),
        (EVENT_COMMENT, "Comment Added"),
        (EVENT_ASSIGNED, "Assigned"),
    ]

    change = models.ForeignKey(
        Change,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_history",
    )

    old_value = models.TextField(
        blank=True,
        default="",
    )

    new_value = models.TextField(
        blank=True,
        default="",
    )

    comment = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Change History"
        verbose_name_plural = "Change History"
        indexes = [
            models.Index(fields=["change", "created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.change} - {self.get_event_type_display()}"

    @classmethod
    def record(
        cls,
        *,
        change,
        event_type,
        user=None,
        comment="",
        old_value="",
        new_value="",
        metadata=None,
    ):
        return cls.objects.create(
            change=change,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )
