from __future__ import annotations

from apps.service_desk.models import Queue, Ticket
from apps.service_desk.services.assignment_service import AssignmentService


class RoutingEngine:
    """Route tickets to queues based on AI category hints."""

    CATEGORY_QUEUE = {
        "network": "network",
        "email": "service-desk",
        "hardware": "service-desk",
        "access": "service-desk",
        "software": "service-desk",
        "telephony": "service-desk",
    }

    @classmethod
    def route(cls, ticket: Ticket, category_code: str = "", auto_assign: bool = True) -> Ticket:
        if not ticket.company_id:
            return ticket
        code = category_code or ticket.ai_category_suggestion or "service-desk"
        queue_code = cls.CATEGORY_QUEUE.get(code, "service-desk")
        queue = Queue.objects.filter(
            company=ticket.company, code=queue_code, is_active=True
        ).first()
        if queue is None:
            queue = Queue.objects.filter(company=ticket.company, is_active=True).first()
        if queue and ticket.queue_id != queue.pk:
            ticket.queue = queue
            ticket.save(update_fields=["queue", "updated_at"])
        if auto_assign and not ticket.assignee_id:
            AssignmentService.auto_assign(ticket)
        return ticket
