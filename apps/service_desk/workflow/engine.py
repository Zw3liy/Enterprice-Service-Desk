"""Workflow engine — status transition guards + automation bridge."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.service_desk.models import Status, Ticket
from apps.service_desk.services.automation_service import AutomationService


class WorkflowEngine:
    ALLOWED = {
        Status.CategoryChoice.NEW: {
            Status.CategoryChoice.IN_PROGRESS,
            Status.CategoryChoice.PENDING,
            Status.CategoryChoice.CANCELLED,
        },
        Status.CategoryChoice.IN_PROGRESS: {
            Status.CategoryChoice.PENDING,
            Status.CategoryChoice.RESOLVED,
            Status.CategoryChoice.CANCELLED,
            Status.CategoryChoice.IN_PROGRESS,
        },
        Status.CategoryChoice.PENDING: {
            Status.CategoryChoice.IN_PROGRESS,
            Status.CategoryChoice.RESOLVED,
            Status.CategoryChoice.CANCELLED,
        },
        Status.CategoryChoice.RESOLVED: {
            Status.CategoryChoice.CLOSED,
            Status.CategoryChoice.IN_PROGRESS,
        },
        Status.CategoryChoice.CLOSED: set(),
        Status.CategoryChoice.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, current: Status | None, new: Status | None) -> bool:
        if new is None:
            return False
        if current is None:
            return True
        if current.pk == new.pk:
            return True
        allowed = cls.ALLOWED.get(current.category, set())
        return new.category in allowed

    @classmethod
    def transition(cls, ticket: Ticket, new_status: Status, actor=None) -> Ticket:
        if not cls.can_transition(ticket.status, new_status):
            raise ValidationError(
                f"Illegal transition from {ticket.status} to {new_status}"
            )
        ticket.status = new_status
        if new_status.category == Status.CategoryChoice.RESOLVED:
            ticket.mark_resolved()
        if new_status.category == Status.CategoryChoice.CLOSED:
            ticket.mark_closed()
        ticket.save()
        AutomationService.dispatch("status.changed", ticket=ticket)
        return ticket
