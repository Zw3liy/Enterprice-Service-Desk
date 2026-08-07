from django.conf import settings
from django.db import models
from django.utils import timezone

from .problem import Problem


class ProblemHistory(models.Model):
    """
    Immutable audit trail for problem events.
    """

    EVENT_CREATED = "created"
    EVENT_UPDATED = "updated"
    EVENT_STATUS_CHANGED = "status_changed"
    EVENT_ASSIGNED = "assigned"
    EVENT_UNASSIGNED = "unassigned"
    EVENT_ROOT_CAUSE_UPDATED = "root_cause_updated"
    EVENT_WORKAROUND_UPDATED = "workaround_updated"
    EVENT_KNOWN_ERROR_DECLARED = "known_error_declared"
    EVENT_TICKET_LINKED = "ticket_linked"
    EVENT_TICKET_UNLINKED = "ticket_unlinked"
    EVENT_COMMENT = "comment"
    EVENT_CLOSED = "closed"
    EVENT_REOPENED = "reopened"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_UPDATED, "Updated"),
        (EVENT_STATUS_CHANGED, "Status Changed"),
        (EVENT_ASSIGNED, "Assigned"),
        (EVENT_UNASSIGNED, "Unassigned"),
        (EVENT_ROOT_CAUSE_UPDATED, "Root Cause Updated"),
        (EVENT_WORKAROUND_UPDATED, "Workaround Updated"),
        (EVENT_KNOWN_ERROR_DECLARED, "Known Error Declared"),
        (EVENT_TICKET_LINKED, "Ticket Linked"),
        (EVENT_TICKET_UNLINKED, "Ticket Unlinked"),
        (EVENT_COMMENT, "Comment Added"),
        (EVENT_CLOSED, "Closed"),
        (EVENT_REOPENED, "Reopened"),
    ]

    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problem_history",
    )

    from_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    to_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
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
        verbose_name = "Problem History"
        verbose_name_plural = "Problem History"

        indexes = [
            models.Index(fields=["problem", "created_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["performed_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.problem} - {self.get_event_type_display()}"

    @property
    def is_status_change(self):
        return self.event_type == self.EVENT_STATUS_CHANGED

    @property
    def is_assignment_change(self):
        return self.event_type in {
            self.EVENT_ASSIGNED,
            self.EVENT_UNASSIGNED,
        }

    @classmethod
    def record(
        cls,
        *,
        problem,
        event_type,
        user=None,
        comment="",
        from_status="",
        to_status="",
        old_value="",
        new_value="",
        metadata=None,
    ):
        return cls.objects.create(
            problem=problem,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            from_status=from_status,
            to_status=to_status,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )
