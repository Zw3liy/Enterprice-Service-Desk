from apps.service_desk.models import Ticket
from apps.service_desk.services.sla.sla_service import SLAService


class SLASelector:
    """Read-only queries for SLA-related ticket information."""

    @staticmethod
    def get_tickets_breached_sla(user=None):
        """
        Return tickets whose SLA deadline has been breached.

        The selector starts from the ticket queryset and applies
        requester/creator scoping for non-staff users when the
        corresponding field exists on the Ticket model.
        """
        queryset = Ticket.objects.all()

        if user is not None and not getattr(user, "is_superuser", False):
            if not getattr(user, "is_staff", False):
                requester_field = getattr(Ticket, "requester", None)
                created_by_field = getattr(Ticket, "created_by", None)

                if requester_field is not None:
                    queryset = queryset.filter(requester=user)
                elif created_by_field is not None:
                    queryset = queryset.filter(created_by=user)

        breached = []

        for ticket in queryset:
            if SLAService.check_sla_breach(ticket):
                breached.append(ticket)

        return breached

    @staticmethod
    def get_sla_deadline(ticket):
        """Return the calculated SLA deadline for a ticket."""
        return SLAService.calculate_sla_deadline(ticket)
