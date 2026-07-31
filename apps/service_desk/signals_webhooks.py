"""Dispatch outbound webhooks for ticket domain events."""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.service_desk.models import Ticket, TicketComment

logger = logging.getLogger(__name__)


def _safe_dispatch(company, event: str, payload: dict) -> None:
    if company is None:
        return
    try:
        from apps.webhooks.services import WebhookService

        WebhookService.dispatch(company, event, payload)
    except Exception:  # noqa: BLE001
        logger.exception("webhook_dispatch_failed event=%s", event)


@receiver(post_save, sender=Ticket)
def ticket_webhook(sender, instance: Ticket, created: bool, **kwargs):
    event = "ticket.created" if created else "ticket.updated"
    _safe_dispatch(
        instance.company,
        event,
        {
            "id": instance.pk,
            "ticket_number": instance.ticket_number,
            "title": instance.title,
            "status_id": instance.status_id,
            "priority_id": instance.priority_id,
            "assignee_id": instance.assignee_id,
        },
    )


@receiver(post_save, sender=TicketComment)
def comment_webhook(sender, instance: TicketComment, created: bool, **kwargs):
    if not created:
        return
    ticket = instance.ticket
    _safe_dispatch(
        ticket.company,
        "comment.added",
        {
            "ticket_id": ticket.pk,
            "ticket_number": ticket.ticket_number,
            "comment_id": instance.pk,
            "is_internal": instance.is_internal,
        },
    )
