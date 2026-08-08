from datetime import timedelta
from django.utils.timezone import now, is_aware
from apps.service_desk.models import Ticket, SLAPolicy


class SLAService:
    """ Service for SLA calculation, breach detection, and related business logic. """

    @staticmethod
    def calculate_sla_deadline(ticket: Ticket) -> 'datetime':
        """ Calculate the SLA deadline for a ticket."""
        if not ticket.sla_policy:
            return None
        duration = ticket.sla_policy.duration()
        if not is_aware(ticket.created_at):
            # Ensure timezone aware
            created_at = now()
        else:
            created_at = ticket.created_at
        deadline = created_at + duration
        return deadline

    @staticmethod
    def check_sla_breach(ticket: Ticket) -> bool:
        """ Check if the SLA deadline is breached."""
        deadline = SLAService.calculate_sla_deadline(ticket)
        if deadline is None:
            return False
        current_time = now()
        return current_time > deadline
