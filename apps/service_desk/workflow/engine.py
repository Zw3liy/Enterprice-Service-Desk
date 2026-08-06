"""
Enterprise Service Desk
Workflow Engine

Responsibilities
----------------
- Executes ticket workflow transitions.
- Validates allowed status changes.
- Records audit history.
- Updates ticket timestamps.
"""

from django.db import transaction
from django.utils import timezone

from apps.service_desk.models import (
    Ticket,
    TicketHistory,
)

from .rules import validate_transition


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""


class WorkflowEngine:
    """
    Enterprise workflow engine.
    """

    @staticmethod
    @transaction.atomic
    def transition(
        *,
        ticket: Ticket,
        new_status: str,
        user,
        notes: str = "",
    ) -> Ticket:
        """
        Execute a status transition.

        Raises:
            WorkflowError
        """

        result = validate_transition(
            ticket=ticket,
            new_status=new_status,
        )

        if not result.success:
            raise WorkflowError(result.message)

        previous_status = ticket.status

        ticket.status = new_status
        ticket.updated_at = timezone.now()

        ticket.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        TicketHistory.objects.create(
            ticket=ticket,
            action="status_changed",
            performed_by=user,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            metadata={
                "workflow": "default",
            },
        )

        return ticket

    @staticmethod
    def available_transitions(ticket: Ticket) -> list[str]:
        """
        Returns all available next states.
        """

        from .rules import allowed_statuses

        return sorted(
            allowed_statuses(ticket.status)
        )

    @staticmethod
    def close(
        *,
        ticket: Ticket,
        user,
        notes: str = "",
    ):
        return WorkflowEngine.transition(
            ticket=ticket,
            new_status="closed",
            user=user,
            notes=notes,
        )

    @staticmethod
    def resolve(
        *,
        ticket: Ticket,
        user,
        notes: str = "",
    ):
        return WorkflowEngine.transition(
            ticket=ticket,
            new_status="resolved",
            user=user,
            notes=notes,
        )

    @staticmethod
    def start_progress(
        *,
        ticket: Ticket,
        user,
        notes: str = "",
    ):
        return WorkflowEngine.transition(
            ticket=ticket,
            new_status="in_progress",
            user=user,
            notes=notes,
        )

    @staticmethod
    def pend(
        *,
        ticket: Ticket,
        user,
        notes: str = "",
    ):
        return WorkflowEngine.transition(
            ticket=ticket,
            new_status="pending",
            user=user,
            notes=notes,
        )

    @staticmethod
    def reopen(
        *,
        ticket: Ticket,
        user,
        notes: str = "",
    ):
        return WorkflowEngine.transition(
            ticket=ticket,
            new_status="in_progress",
            user=user,
            notes=notes,
        )