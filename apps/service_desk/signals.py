"""Domain signals for ticket lifecycle side-effects."""

from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.service_desk.models import Ticket, TicketComment

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Ticket)
def ticket_pre_save(sender, instance: Ticket, **kwargs) -> None:
    if instance.pk:
        try:
            previous = Ticket.objects.get(pk=instance.pk)
            instance._previous_status_id = previous.status_id  # type: ignore[attr-defined]
            instance._previous_assignee_id = previous.assignee_id  # type: ignore[attr-defined]
        except Ticket.DoesNotExist:
            instance._previous_status_id = None  # type: ignore[attr-defined]
            instance._previous_assignee_id = None  # type: ignore[attr-defined]
    else:
        instance._previous_status_id = None  # type: ignore[attr-defined]
        instance._previous_assignee_id = None  # type: ignore[attr-defined]


@receiver(post_save, sender=Ticket)
def ticket_post_save(sender, instance: Ticket, created: bool, **kwargs) -> None:
    from apps.service_desk.services.automation_service import AutomationService
    from apps.service_desk.services.notification_service import NotificationService
    from apps.service_desk.services.audit_service import AuditService

    if created:
        AuditService.log(
            action="ticket.created",
            ticket=instance,
            company=instance.company,
            message=f"Ticket {instance.ticket_number} created",
            metadata={"title": instance.title},
        )
        AutomationService.dispatch("ticket.created", ticket=instance)
        NotificationService.notify_ticket_created(instance)
        try:
            from apps.event_engine.services import EventBus

            EventBus.publish(
                "ticket.created",
                {
                    "id": instance.pk,
                    "ticket_number": instance.ticket_number,
                    "title": instance.title,
                },
                company=instance.company,
                aggregate_type="ticket",
                aggregate_id=str(instance.pk),
            )
        except Exception:
            pass
        return

    prev_status = getattr(instance, "_previous_status_id", None)
    if prev_status != instance.status_id:
        AuditService.log(
            action="ticket.status_changed",
            ticket=instance,
            company=instance.company,
            message=f"Status changed on {instance.ticket_number}",
            metadata={"from": prev_status, "to": instance.status_id},
        )
        AutomationService.dispatch("status.changed", ticket=instance)
        NotificationService.notify_status_changed(instance)

    prev_assignee = getattr(instance, "_previous_assignee_id", None)
    if prev_assignee != instance.assignee_id and instance.assignee_id:
        AuditService.log(
            action="ticket.assigned",
            ticket=instance,
            company=instance.company,
            message=f"Ticket assigned to user {instance.assignee_id}",
            metadata={"from": prev_assignee, "to": instance.assignee_id},
        )
        AutomationService.dispatch("ticket.assigned", ticket=instance)
        NotificationService.notify_assigned(instance)


@receiver(post_save, sender=TicketComment)
def comment_post_save(sender, instance: TicketComment, created: bool, **kwargs) -> None:
    if not created:
        return
    from apps.service_desk.services.automation_service import AutomationService
    from apps.service_desk.services.notification_service import NotificationService
    from apps.service_desk.services.audit_service import AuditService

    ticket = instance.ticket
    if not instance.is_internal and not instance.is_system:
        ticket.mark_first_response()
        ticket.save(
            update_fields=[
                "first_response_at",
                "sla_response_breached",
                "updated_at",
            ]
        )

    AuditService.log(
        action="comment.added",
        ticket=ticket,
        company=ticket.company,
        actor=instance.author,
        message="Comment added",
        metadata={"internal": instance.is_internal},
    )
    AutomationService.dispatch("comment.added", ticket=ticket, comment=instance)
    NotificationService.notify_comment_added(instance)
