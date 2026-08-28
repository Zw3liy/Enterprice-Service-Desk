from django.conf import settings
from django.db import models
from django.utils import timezone

from .change import Change
from .department import Department


class Release(models.Model):
    """
    A governed release record (ITIL Release Management).

    Requesters have no access at all — same rationale as
    ``Change`` (internal IT governance, not requester-facing).
    See ``security.policies.get_release_queryset``.
    """

    ENVIRONMENT_DEVELOPMENT = "development"
    ENVIRONMENT_STAGING = "staging"
    ENVIRONMENT_PRODUCTION = "production"

    ENVIRONMENT_CHOICES = [
        (ENVIRONMENT_DEVELOPMENT, "Development"),
        (ENVIRONMENT_STAGING, "Staging"),
        (ENVIRONMENT_PRODUCTION, "Production"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_APPROVED = "approved"
    STATUS_SCHEDULED = "scheduled"
    STATUS_DEPLOYING = "deploying"
    STATUS_VALIDATION = "validation"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_ROLLED_BACK = "rolled_back"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_DEPLOYING, "Deploying"),
        (STATUS_VALIDATION, "Validation"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_ROLLED_BACK, "Rolled Back"),
    ]

    # A Change may only be linked to a Release once it has cleared
    # CAB approval and has not failed/been rejected/rolled back — the
    # "approved eligibility boundary" the mission requires.
    CHANGE_ELIGIBLE_STATUSES = {
        Change.STATUS_APPROVED,
        Change.STATUS_SCHEDULED,
        Change.STATUS_IMPLEMENTING,
        Change.STATUS_VALIDATION,
        Change.STATUS_COMPLETED,
    }

    SCHEDULABLE_STATUSES = {STATUS_SCHEDULED, STATUS_DEPLOYING}

    name = models.CharField(
        max_length=200,
    )

    version = models.CharField(
        max_length=50,
        help_text="e.g. 2026.09.1",
    )

    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default=ENVIRONMENT_STAGING,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="releases",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_releases",
    )

    changes = models.ManyToManyField(
        Change,
        blank=True,
        related_name="releases",
    )

    deployment_plan = models.TextField(
        blank=True,
        default="",
    )

    validation_plan = models.TextField(
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

    outcome = models.TextField(
        blank=True,
        default="",
        help_text="Recorded on completion, failure or rollback.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Release"
        verbose_name_plural = "Releases"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_release_name_per_version",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["department"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["environment"]),
            models.Index(fields=["scheduled_start", "scheduled_end"]),
        ]

    def __str__(self):
        return f"{self.name} {self.version}"

    @property
    def is_open(self):
        return self.status not in {
            self.STATUS_COMPLETED,
            self.STATUS_ROLLED_BACK,
        }


class ReleaseApproval(models.Model):
    DECISION_APPROVED = "approved"
    DECISION_REJECTED = "rejected"

    DECISION_CHOICES = [
        (DECISION_APPROVED, "Approved"),
        (DECISION_REJECTED, "Rejected"),
    ]

    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_approvals",
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
        verbose_name = "Release Approval"
        verbose_name_plural = "Release Approvals"
        indexes = [
            models.Index(fields=["release", "decided_at"]),
        ]

    def __str__(self):
        return f"{self.release} - {self.get_decision_display()}"


class ReleaseHistory(models.Model):
    EVENT_CREATED = "created"
    EVENT_APPROVED = "approved"
    EVENT_REJECTED = "rejected"
    EVENT_SCHEDULED = "scheduled"
    EVENT_DEPLOYING = "deploying"
    EVENT_VALIDATION = "validation"
    EVENT_COMPLETED = "completed"
    EVENT_FAILED = "failed"
    EVENT_ROLLED_BACK = "rolled_back"
    EVENT_CHANGE_LINKED = "change_linked"
    EVENT_CHANGE_UNLINKED = "change_unlinked"
    EVENT_OWNER_ASSIGNED = "owner_assigned"
    EVENT_COMMENT = "comment"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_APPROVED, "Approved"),
        (EVENT_REJECTED, "Rejected"),
        (EVENT_SCHEDULED, "Scheduled"),
        (EVENT_DEPLOYING, "Deploying"),
        (EVENT_VALIDATION, "Validation"),
        (EVENT_COMPLETED, "Completed"),
        (EVENT_FAILED, "Failed"),
        (EVENT_ROLLED_BACK, "Rolled Back"),
        (EVENT_CHANGE_LINKED, "Change Linked"),
        (EVENT_CHANGE_UNLINKED, "Change Unlinked"),
        (EVENT_OWNER_ASSIGNED, "Owner Assigned"),
        (EVENT_COMMENT, "Comment Added"),
    ]

    release = models.ForeignKey(
        Release,
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
        related_name="release_history",
    )

    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    comment = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Release History"
        verbose_name_plural = "Release History"
        indexes = [
            models.Index(fields=["release", "created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.release} - {self.get_event_type_display()}"

    @classmethod
    def record(
        cls,
        *,
        release,
        event_type,
        user=None,
        comment="",
        old_value="",
        new_value="",
        metadata=None,
    ):
        return cls.objects.create(
            release=release,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )
