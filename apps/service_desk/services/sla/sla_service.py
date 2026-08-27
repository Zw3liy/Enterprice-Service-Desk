from datetime import timedelta

from django.utils import timezone

from apps.service_desk.models import Ticket


class SLAService:
    """Business logic for calculating and evaluating ticket SLA deadlines."""

    @staticmethod
    def calculate_sla_deadline(ticket):
        """
        Calculate the SLA deadline for a ticket.

        Returns:
            datetime | None: The calculated SLA deadline, or None when
            the ticket has no SLA policy or creation timestamp.
        """
        if ticket is None:
            return None

        policy = getattr(ticket, "sla_policy", None)

        if policy is None:
            return None

        created_at = getattr(ticket, "created_at", None)

        if created_at is None:
            return None

        duration_minutes = getattr(policy, "duration_minutes", None)

        if duration_minutes is None:
            return None

        return created_at + timedelta(minutes=duration_minutes)

    @staticmethod
    def check_sla_breach(ticket):
        """
        Determine whether a ticket has breached its configured SLA.

        Resolved and closed tickets are not considered breached.
        Tickets without an SLA policy or creation timestamp cannot
        currently be evaluated as breached.
        """
        deadline = SLAService.calculate_sla_deadline(ticket)

        if deadline is None:
            return False

        status = getattr(ticket, "status", None)

        terminal_statuses = set()

        resolved_status = getattr(Ticket, "STATUS_RESOLVED", None)
        closed_status = getattr(Ticket, "STATUS_CLOSED", None)

        if resolved_status is not None:
            terminal_statuses.add(resolved_status)

        if closed_status is not None:
            terminal_statuses.add(closed_status)

        if status in terminal_statuses:
            return False

        return timezone.now() >= deadline
