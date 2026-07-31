from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.field_service.models import WorkOrder
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService
from apps.service_desk.services.ticket_service import TicketService


class FieldService:
    @classmethod
    @transaction.atomic
    def create_work_order(
        cls,
        ticket,
        *,
        title: str = "",
        description: str = "",
        location: str = "",
        technician=None,
        scheduled_start=None,
        scheduled_end=None,
        actor=None,
    ) -> WorkOrder:
        wo = WorkOrder.objects.create(
            company=ticket.company,
            ticket=ticket,
            title=title or f"On-site for {ticket.ticket_number}",
            description=description or ticket.description,
            location=location,
            technician=technician,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
        )
        if technician:
            NotificationService.create(
                recipient=technician,
                subject=f"[{wo.number}] Work order assigned",
                body=wo.title,
                ticket=ticket,
                send_email=True,
            )
        AuditService.log(
            action="field.work_order_created",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message=wo.number,
            object_type="work_order",
            object_id=str(wo.pk),
        )
        return wo

    @classmethod
    def dispatch(cls, work_order: WorkOrder, technician=None, actor=None) -> WorkOrder:
        if technician:
            work_order.technician = technician
        work_order.state = WorkOrder.State.DISPATCHED
        work_order.save()
        if work_order.technician_id:
            NotificationService.create(
                recipient=work_order.technician,
                subject=f"[{work_order.number}] Dispatched",
                body=work_order.title,
                ticket=work_order.ticket,
                send_email=True,
            )
        return work_order

    @classmethod
    def check_in(cls, work_order: WorkOrder, actor=None) -> WorkOrder:
        work_order.state = WorkOrder.State.ON_SITE
        work_order.actual_start = timezone.now()
        work_order.save(update_fields=["state", "actual_start", "updated_at"])
        TicketService.add_comment(
            work_order.ticket,
            body=f"Technician on site for {work_order.number}",
            author=actor or work_order.technician,
            is_system=True,
        )
        return work_order

    @classmethod
    def complete(cls, work_order: WorkOrder, *, notes: str = "", actor=None) -> WorkOrder:
        work_order.state = WorkOrder.State.COMPLETED
        work_order.actual_end = timezone.now()
        work_order.resolution_notes = notes
        work_order.save()
        if notes:
            TicketService.add_comment(
                work_order.ticket,
                body=f"Work order {work_order.number} completed: {notes}",
                author=actor or work_order.technician,
                is_internal=False,
            )
        return work_order
