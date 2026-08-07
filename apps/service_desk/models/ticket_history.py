from django.conf import settings
from django.db import models
from django.utils import timezone

from .ticket import Ticket


class TicketHistory(models.Model):
    """
    Immutable audit trail for ticket events.
    """

    EVENT_CREATED = "created"
    EVENT_UPDATED = "updated"
    EVENT_STATUS_CHANGED = "status_changed"
    EVENT_ASSIGNED = "assigned"
    EVENT_UNASSIGNED = "unassigned"
    EVENT_PRIORITY_CHANGED = "priority_changed"
    EVENT_URGENCY_CHANGED = "urgency_changed"
    EVENT_DEPARTMENT_CHANGED = "department_changed"
    EVENT_REQUEST_TYPE_CHANGED = "request_type_changed"
    EVENT_COMMENT = "comment"
    EVENT_WORK_NOTE = "work_note"
    EVENT_ATTACHMENT = "attachment"
    EVENT_CLOSED = "closed"
    EVENT_REOPENED = "reopened"
    EVENT_CONFIRMED = "requester_confirmed"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_UPDATED, "Updated"),
        (EVENT_STATUS_CHANGED, "Status Changed"),
        (EVENT_ASSIGNED, "Assigned"),
        (EVENT_UNASSIGNED, "Unassigned"),
        (EVENT_PRIORITY_CHANGED, "Priority Changed"),
        (EVENT_URGENCY_CHANGED, "Urgency Changed"),
        (EVENT_DEPARTMENT_CHANGED, "Department Changed"),
        (EVENT_REQUEST_TYPE_CHANGED, "Request Type Changed"),
        (EVENT_COMMENT, "Comment Added"),
        (EVENT_WORK_NOTE, "Work Note Added"),
        (EVENT_ATTACHMENT, "Attachment Added"),
        (EVENT_CLOSED, "Closed"),
        (EVENT_REOPENED, "Reopened"),
        (EVENT_CONFIRMED, "Requester Confirmed"),
    ]

    ticket = models.ForeignKey(
        Ticket,
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
        related_name="ticket_history",
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
        verbose_name = "Ticket History"
        verbose_name_plural = "Ticket History"

        indexes = [
            models.Index(fields=["ticket", "created_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["performed_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.ticket} - {self.get_event_type_display()}"

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
        ticket,
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
            ticket=ticket,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            from_status=from_status,
            to_status=to_status,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )