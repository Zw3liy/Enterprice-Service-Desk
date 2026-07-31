"""Notification delivery (in-app + email)."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from apps.service_desk.models import Notification, Ticket, TicketComment

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    @staticmethod
    def _recipients_for_ticket(ticket: Ticket) -> list:
        users = []
        if ticket.assignee_id:
            users.append(ticket.assignee)
        if ticket.requester_user_id and ticket.requester_user_id != ticket.assignee_id:
            users.append(ticket.requester_user)
        for watcher in ticket.watchers.select_related("user").all():
            if watcher.user_id not in {u.pk for u in users if u}:
                users.append(watcher.user)
        return [u for u in users if u is not None]

    @classmethod
    def create(
        cls,
        *,
        recipient,
        subject: str,
        body: str,
        ticket: Optional[Ticket] = None,
        channel: str = Notification.Channel.IN_APP,
        payload: Optional[dict] = None,
        send_email: bool = False,
    ) -> Notification:
        notification = Notification.objects.create(
            company=ticket.company if ticket else None,
            recipient=recipient,
            ticket=ticket,
            channel=channel,
            subject=subject,
            body=body,
            payload=payload or {},
            status=Notification.Status.PENDING,
        )
        if send_email or channel == Notification.Channel.EMAIL:
            cls._deliver_email(notification)
        else:
            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            notification.save(update_fields=["status", "sent_at", "updated_at"])
        return notification

    @classmethod
    def _deliver_email(cls, notification: Notification) -> None:
        email = getattr(notification.recipient, "email", "") or ""
        if not email:
            notification.status = Notification.Status.FAILED
            notification.error_message = "Recipient has no email address"
            notification.save(update_fields=["status", "error_message", "updated_at"])
            return
        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            notification.channel = Notification.Channel.EMAIL
            notification.save(
                update_fields=["status", "sent_at", "channel", "updated_at"]
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("email delivery failed")
            notification.status = Notification.Status.FAILED
            notification.error_message = str(exc)
            notification.save(update_fields=["status", "error_message", "updated_at"])

    @classmethod
    def notify_many(
        cls,
        recipients: Iterable,
        *,
        subject: str,
        body: str,
        ticket: Optional[Ticket] = None,
        send_email: bool = False,
    ) -> list[Notification]:
        created = []
        seen = set()
        for user in recipients:
            if not user or user.pk in seen:
                continue
            seen.add(user.pk)
            created.append(
                cls.create(
                    recipient=user,
                    subject=subject,
                    body=body,
                    ticket=ticket,
                    send_email=send_email,
                )
            )
        return created

    @classmethod
    def notify_ticket_created(cls, ticket: Ticket) -> None:
        recipients = cls._recipients_for_ticket(ticket)
        if ticket.queue_id:
            for member in ticket.queue.members.all():
                recipients.append(member)
        cls.notify_many(
            recipients,
            subject=f"[{ticket.ticket_number}] New ticket: {ticket.title}",
            body=ticket.description or ticket.title,
            ticket=ticket,
        )

    @classmethod
    def notify_assigned(cls, ticket: Ticket) -> None:
        if not ticket.assignee_id:
            return
        cls.create(
            recipient=ticket.assignee,
            subject=f"[{ticket.ticket_number}] Assigned to you",
            body=f"You have been assigned ticket {ticket.ticket_number}: {ticket.title}",
            ticket=ticket,
            send_email=True,
        )

    @classmethod
    def notify_status_changed(cls, ticket: Ticket) -> None:
        status_name = ticket.status.name if ticket.status_id else "updated"
        cls.notify_many(
            cls._recipients_for_ticket(ticket),
            subject=f"[{ticket.ticket_number}] Status → {status_name}",
            body=f"Ticket status is now {status_name}.",
            ticket=ticket,
        )

    @classmethod
    def notify_comment_added(cls, comment: TicketComment) -> None:
        ticket = comment.ticket
        recipients = [
            u
            for u in cls._recipients_for_ticket(ticket)
            if not comment.author_id or u.pk != comment.author_id
        ]
        if comment.is_internal:
            # Internal notes: agents only
            recipients = [
                u
                for u in recipients
                if u.is_staff or hasattr(u, "agent_profile")
            ]
        cls.notify_many(
            recipients,
            subject=f"[{ticket.ticket_number}] New comment",
            body=comment.body[:2000],
            ticket=ticket,
        )

    @classmethod
    def notify_sla_breach(cls, ticket: Ticket, kind: str) -> None:
        recipients = cls._recipients_for_ticket(ticket)
        if ticket.queue_id:
            recipients.extend(list(ticket.queue.members.all()))
        cls.notify_many(
            recipients,
            subject=f"[{ticket.ticket_number}] SLA {kind} breached",
            body=f"SLA {kind} target missed for {ticket.ticket_number}.",
            ticket=ticket,
            send_email=True,
        )

    @staticmethod
    def unread_queryset(user):
        return Notification.objects.filter(
            recipient=user
        ).filter(
            Q(status=Notification.Status.PENDING) | Q(status=Notification.Status.SENT)
        )
