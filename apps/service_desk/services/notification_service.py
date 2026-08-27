"""
Notification boundary.

Design rules this module enforces:

1. **In-app first.** Every notification is a persisted
   ``Notification`` row. Email is an optional *mirror*, never the
   primary channel, so the product is fully usable on a deployment
   with no SMTP configuration — which is the state this repository
   ships in and the state CI runs in.

2. **Fail safe.** A failing mail backend must never roll back or
   break the business operation that triggered it. Every send is
   wrapped and logged; the in-app record survives regardless.

3. **No credentials in the repository.** Host, port, user, password
   and TLS come from environment variables (see ``.env.example``).
   With none set, ``SERVICE_DESK_EMAIL_NOTIFICATIONS`` defaults to
   off and nothing is ever sent.

4. **Respect visibility.** Notifications are only ever addressed to a
   user who is already entitled to the underlying record — a work
   note never reaches a Requester through this path, and the recipient
   set for a ticket is derived from the ticket itself.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.service_desk.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:

    # ==========================================================
    # Core delivery
    # ==========================================================

    @staticmethod
    def _email_enabled() -> bool:
        return bool(
            getattr(settings, "SERVICE_DESK_EMAIL_NOTIFICATIONS", False)
        )

    @staticmethod
    def _send_email(notification: Notification) -> bool:
        """
        Best-effort email mirror. Returns True only on success.
        """

        if not NotificationService._email_enabled():
            return False

        address = (notification.recipient.email or "").strip()

        if not address:
            return False

        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[address],
                fail_silently=False,
            )
        except Exception:
            # A broken or unreachable mail server must not take down
            # the ticket operation that produced this notification.
            logger.exception(
                "Failed to email notification %s to %s",
                notification.pk,
                address,
            )
            return False

        return True

    @staticmethod
    def notify(
        recipient,
        kind: str,
        subject: str,
        body: str = "",
        ticket=None,
        problem=None,
        actor=None,
    ):
        """
        Create one notification.

        Returns None (without raising) when there is nobody to notify
        or when the recipient is the person who performed the action —
        people do not need to be told what they just did.
        """

        if recipient is None or not getattr(recipient, "pk", None):
            return None

        if not getattr(recipient, "is_active", True):
            return None

        if actor is not None and actor.pk == recipient.pk:
            return None

        notification = Notification.objects.create(
            recipient=recipient,
            kind=kind,
            subject=subject[:200],
            body=body,
            ticket=ticket,
            problem=problem,
        )

        if NotificationService._send_email(notification):
            notification.emailed = True
            notification.save(update_fields=["emailed"])

        return notification

    @staticmethod
    def notify_many(recipients, **kwargs):
        seen = set()
        created = []

        for recipient in recipients:
            if recipient is None or recipient.pk in seen:
                continue

            seen.add(recipient.pk)

            notification = NotificationService.notify(recipient, **kwargs)

            if notification:
                created.append(notification)

        return created

    # ==========================================================
    # Ticket events
    # ==========================================================

    @staticmethod
    def notify_assignment(ticket, assignee, actor=None):
        """
        Tell a technician they now own a ticket.
        """

        return NotificationService.notify(
            recipient=assignee,
            kind=Notification.KIND_TICKET_ASSIGNED,
            subject=f"Ticket #{ticket.pk} assigned to you: {ticket.title}",
            body=(
                f"You have been assigned ticket #{ticket.pk} "
                f"({ticket.get_priority_display()} priority).\n\n"
                f"{ticket.description}"
            ),
            ticket=ticket,
            actor=actor,
        )

    @staticmethod
    def notify_status_change(ticket, from_status, to_status, actor=None):
        """
        Tell the people attached to a ticket that it moved.

        Recipients are the requester and the assignee — both already
        entitled to see the ticket. The body carries only the status
        transition, never work-note content.
        """

        labels = dict(ticket.STATUS_CHOICES)

        subject = (
            f"Ticket #{ticket.pk} is now "
            f"{labels.get(to_status, to_status)}"
        )

        body = (
            f"'{ticket.title}' moved from "
            f"{labels.get(from_status, from_status)} to "
            f"{labels.get(to_status, to_status)}."
        )

        if to_status == "awaiting_confirmation":
            return NotificationService.notify(
                recipient=ticket.created_by,
                kind=Notification.KIND_CONFIRMATION_REQUESTED,
                subject=(
                    f"Please confirm the resolution of ticket "
                    f"#{ticket.pk}"
                ),
                body=(
                    f"'{ticket.title}' has been resolved and is waiting "
                    "for your confirmation before it is closed."
                ),
                ticket=ticket,
                actor=actor,
            )

        if to_status == "closed" and from_status == "awaiting_confirmation":
            return NotificationService.notify_many(
                [ticket.assigned_to],
                kind=Notification.KIND_TICKET_CONFIRMED,
                subject=f"Ticket #{ticket.pk} confirmed and closed",
                body=(
                    f"The requester confirmed the resolution of "
                    f"'{ticket.title}'."
                ),
                ticket=ticket,
                actor=actor,
            )

        return NotificationService.notify_many(
            [ticket.created_by, ticket.assigned_to],
            kind=Notification.KIND_TICKET_STATUS,
            subject=subject,
            body=body,
            ticket=ticket,
            actor=actor,
        )

    # ==========================================================
    # SLA events
    # ==========================================================

    @staticmethod
    def notify_sla_escalation(record, escalation):
        """
        Route an SLA warning or breach to the people who can act.

        Assignee first; if the ticket is unassigned, the managers of
        its department, so an unowned breach is not silently dropped.
        """

        ticket = record.ticket

        recipients = []

        if ticket.assigned_to_id:
            recipients.append(ticket.assigned_to)
        elif ticket.department_id:
            recipients.extend(ticket.department.managers.all())

        if not recipients:
            return []

        kind = (
            Notification.KIND_SLA_BREACH
            if escalation.is_breach
            else Notification.KIND_SLA_WARNING
        )

        return NotificationService.notify_many(
            recipients,
            kind=kind,
            subject=(
                f"SLA {escalation.get_kind_display().lower()} on ticket "
                f"#{ticket.pk}"
            ),
            body=f"{ticket.title}\n\n{escalation.detail}",
            ticket=ticket,
        )

    # ==========================================================
    # Problem events
    # ==========================================================

    @staticmethod
    def notify_problem_update(problem, subject, body, actor=None):
        """
        Notify on a significant Problem change.

        Recipients are the investigator and the raiser. Requesters
        cannot access Problem records at all (ADR-010, Decision 1), so
        any recipient who lacks view_problem is dropped rather than
        being sent a notification they could not open.
        """

        candidates = [problem.assigned_to, problem.created_by]

        recipients = [
            user
            for user in candidates
            if user is not None
            and user.has_perm("service_desk.view_problem")
        ]

        return NotificationService.notify_many(
            recipients,
            kind=Notification.KIND_PROBLEM_UPDATE,
            subject=subject,
            body=body,
            problem=problem,
            actor=actor,
        )

    # ==========================================================
    # Read state
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def mark_read(notification, user):
        """
        Mark one notification read.

        The caller must own it — enforced here rather than in the view
        so no future call site can skip the check.
        """

        if notification.recipient_id != user.pk:
            raise PermissionError(
                "A notification can only be read by its recipient."
            )

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])

        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_read(user):
        return Notification.objects.filter(
            recipient=user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
