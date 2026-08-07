from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import (
    Department,
    RequestType,
    Ticket,
    TicketHistory,
)

User = get_user_model()


class TicketService:
    """
    Enterprise Service Desk ticket business service.
    """

    STATUS_FLOW = {
        "open": ["in_progress"],
        "in_progress": ["pending", "resolved"],
        "pending": ["in_progress", "resolved"],
        "resolved": ["closed"],
        "closed": ["open"],
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_ticket(**data: Any) -> Ticket:
        user = data.get("created_by")

        ticket = Ticket.objects.create(**data)

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_CREATED,
            user=user,
            comment="Ticket created.",
            to_status=ticket.status,
        )

        return ticket

    # ==========================================================
    # Update
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def update_ticket(ticket: Ticket, user=None, **fields) -> Ticket:

        changed = {}

        for field, value in fields.items():

            if not hasattr(ticket, field):
                continue

            current = getattr(ticket, field)

            if current != value:
                changed[field] = (current, value)
                setattr(ticket, field, value)

        if not changed:
            return ticket

        ticket.full_clean()
        ticket.save()

        for field, values in changed.items():

            TicketHistory.record(
                ticket=ticket,
                event_type=TicketHistory.EVENT_UPDATED,
                user=user,
                old_value=str(values[0]),
                new_value=str(values[1]),
                comment=f"{field} updated.",
            )

        return ticket

    # ==========================================================
    # Assignment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def assign_ticket(
        ticket: Ticket,
        technician: User,
        user=None,
    ) -> Ticket:

        if technician is None:
            raise ValidationError("Technician is required.")

        if not technician.is_active:
            raise ValidationError("Technician is inactive.")

        previous = ticket.assigned_to

        ticket.assigned_to = technician
        ticket.save(update_fields=["assigned_to", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_ASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=technician.get_username(),
        )

        return ticket

    @staticmethod
    @transaction.atomic
    def unassign_ticket(ticket: Ticket, user=None) -> Ticket:

        previous = ticket.assigned_to

        ticket.assigned_to = None
        ticket.save(update_fields=["assigned_to", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_UNASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
        )

        return ticket

    # ==========================================================
    # Status
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_status(
        ticket: Ticket,
        status: str,
        user=None,
    ) -> Ticket:

        status = status.lower()

        if status not in dict(Ticket.STATUS_CHOICES):
            raise ValidationError("Invalid status.")

        current = ticket.status

        if current == status:
            return ticket

        allowed = TicketService.STATUS_FLOW.get(current, [])

        if status not in allowed:
            raise ValidationError(
                f"Cannot move from {current} to {status}."
            )

        ticket.status = status
        ticket.save(update_fields=["status", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_STATUS_CHANGED,
            user=user,
            from_status=current,
            to_status=status,
        )

        return ticket

    # ==========================================================
    # Priority
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_priority(
        ticket: Ticket,
        priority: str,
        user=None,
    ) -> Ticket:

        if priority not in dict(Ticket.PRIORITY_CHOICES):
            raise ValidationError("Invalid priority.")

        previous = ticket.priority

        ticket.priority = priority
        ticket.save(update_fields=["priority", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_PRIORITY_CHANGED,
            user=user,
            old_value=previous,
            new_value=priority,
        )

        return ticket

    # ==========================================================
    # Urgency
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_urgency(
        ticket: Ticket,
        urgency: str,
        user=None,
    ) -> Ticket:

        if urgency not in dict(Ticket.URGENCY_CHOICES):
            raise ValidationError("Invalid urgency.")

        previous = ticket.urgency

        ticket.urgency = urgency
        ticket.save(update_fields=["urgency", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_URGENCY_CHANGED,
            user=user,
            old_value=previous,
            new_value=urgency,
        )

        return ticket

    # ==========================================================
    # Department
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_department(
        ticket: Ticket,
        department: Department,
        user=None,
    ) -> Ticket:

        previous = ticket.department

        ticket.department = department
        ticket.save(update_fields=["department", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_DEPARTMENT_CHANGED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=str(department),
        )

        return ticket

    # ==========================================================
    # Request Type
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_request_type(
        ticket: Ticket,
        request_type: RequestType,
        user=None,
    ) -> Ticket:

        previous = ticket.request_type

        ticket.request_type = request_type
        ticket.save(update_fields=["request_type", "updated_at"])

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_REQUEST_TYPE_CHANGED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=str(request_type),
        )

        return ticket

    # ==========================================================
    # Comments
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_comment(
        ticket: Ticket,
        comment: str,
        user=None,
    ) -> TicketHistory:

        if not comment.strip():
            raise ValidationError("Comment cannot be empty.")

        return TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_COMMENT,
            user=user,
            comment=comment.strip(),
        )

    # ==========================================================
    # Close
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def close_ticket(
        ticket: Ticket,
        user=None,
    ) -> Ticket:

        if ticket.status != "resolved":
            raise ValidationError(
                "Only resolved tickets can be closed."
            )

        return TicketService.change_status(
            ticket,
            "closed",
            user=user,
        )

    # ==========================================================
    # Reopen
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def reopen_ticket(
        ticket: Ticket,
        user=None,
    ) -> Ticket:

        if ticket.status != "closed":
            raise ValidationError(
                "Only closed tickets can be reopened."
            )

        return TicketService.change_status(
            ticket,
            "open",
            user=user,
        )

    # ==========================================================
    # Delete
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def delete_ticket(ticket: Ticket) -> None:
        ticket.delete()