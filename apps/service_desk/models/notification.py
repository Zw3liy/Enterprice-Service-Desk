"""
Internal notification record.

The service desk's notification boundary is in-app first: a
``Notification`` row is always written, and email is an optional
mirror controlled by configuration (see ``settings.py``,
``SERVICE_DESK_EMAIL_NOTIFICATIONS``). That ordering matters — the
product must remain fully usable on a deployment with no SMTP
credentials at all, which is the state this repository ships in.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from .problem import Problem
from .ticket import Ticket


class Notification(models.Model):
    """
    One delivered notification for one recipient.
    """

    KIND_TICKET_ASSIGNED = "ticket_assigned"
    KIND_TICKET_STATUS = "ticket_status_changed"
    KIND_CONFIRMATION_REQUESTED = "confirmation_requested"
    KIND_TICKET_CONFIRMED = "ticket_confirmed"
    KIND_SLA_WARNING = "sla_warning"
    KIND_SLA_BREACH = "sla_breach"
    KIND_PROBLEM_UPDATE = "problem_update"
    KIND_SERVICE_REQUEST_APPROVED = "service_request_approved"
    KIND_SERVICE_REQUEST_REJECTED = "service_request_rejected"
    KIND_SERVICE_REQUEST_FULFILLED = "service_request_fulfilled"

    KIND_CHOICES = [
        (KIND_TICKET_ASSIGNED, "Ticket Assigned"),
        (KIND_TICKET_STATUS, "Ticket Status Changed"),
        (KIND_CONFIRMATION_REQUESTED, "Confirmation Requested"),
        (KIND_TICKET_CONFIRMED, "Ticket Confirmed"),
        (KIND_SLA_WARNING, "SLA Warning"),
        (KIND_SLA_BREACH, "SLA Breach"),
        (KIND_PROBLEM_UPDATE, "Problem Update"),
        (KIND_SERVICE_REQUEST_APPROVED, "Service Request Approved"),
        (KIND_SERVICE_REQUEST_REJECTED, "Service Request Rejected"),
        (KIND_SERVICE_REQUEST_FULFILLED, "Service Request Fulfilled"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_desk_notifications",
    )

    kind = models.CharField(
        max_length=40,
        choices=KIND_CHOICES,
        db_index=True,
    )

    subject = models.CharField(
        max_length=200,
    )

    body = models.TextField(
        blank=True,
        default="",
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    emailed = models.BooleanField(
        default=False,
        help_text=(
            "True when an email mirror of this notification was "
            "successfully handed to the configured email backend."
        ),
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["recipient", "read_at"]),
            models.Index(fields=["kind"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} → {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None

    def target_url(self):
        """
        Where clicking this notification should land.
        """

        from django.urls import reverse

        if self.ticket_id:
            return reverse(
                "service_desk:ticket_detail", args=[self.ticket_id]
            )

        if self.problem_id:
            return reverse(
                "service_desk:problem_detail", args=[self.problem_id]
            )

        return reverse("service_desk:notification_list")
