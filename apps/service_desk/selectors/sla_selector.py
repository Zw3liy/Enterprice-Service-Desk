from django.utils.timezone import now
from apps.service_desk.models import Ticket
from apps.service_desk.services.sla_service import SLAService


class SLASelector:

    @staticmethod
    def get_tickets_breached_sla(user):
        """Return accessible tickets whose SLA deadline has been breached."""

        from apps.service_desk.security.policies import get_ticket_queryset

        queryset = get_ticket_queryset(user)

        current_time = now()

        breached_ids = []

        for ticket in queryset.filter(
            sla_policy__isnull=False
        ).iterator():
            deadline = SLAService.calculate_sla_deadline(ticket)

            if deadline is not None and deadline < current_time:
                breached_ids.append(ticket.pk)

        return queryset.filter(pk__in=breached_ids)