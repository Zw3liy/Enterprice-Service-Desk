from __future__ import annotations

from apps.service_desk.models import Escalation, Ticket
from apps.service_desk.services.sla_service import SLAService


class EscalationEngine:
    @staticmethod
    def evaluate(ticket: Ticket) -> dict:
        return SLAService.evaluate_ticket(ticket)

    @staticmethod
    def open_escalations(company=None):
        qs = Escalation.objects.filter(state=Escalation.State.OPEN).select_related(
            "ticket", "policy", "sla"
        )
        if company is not None:
            qs = qs.filter(ticket__company=company)
        return qs

    @staticmethod
    def acknowledge(escalation: Escalation, user=None) -> Escalation:
        from django.utils import timezone

        escalation.state = Escalation.State.ACKNOWLEDGED
        escalation.acknowledged_at = timezone.now()
        escalation.acknowledged_by = user
        escalation.save(
            update_fields=["state", "acknowledged_at", "acknowledged_by", "updated_at"]
        )
        return escalation

    @staticmethod
    def resolve(escalation: Escalation) -> Escalation:
        from django.utils import timezone

        escalation.state = Escalation.State.RESOLVED
        escalation.resolved_at = timezone.now()
        escalation.save(update_fields=["state", "resolved_at", "updated_at"])
        return escalation
