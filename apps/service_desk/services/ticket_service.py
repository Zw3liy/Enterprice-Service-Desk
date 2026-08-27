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
        "resolved": ["awaiting_confirmation"],
        "awaiting_confirmation": ["closed"],
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

        # Start the SLA clock. No-op when no policy is configured for
        # this priority/department — SLA tracking is opt-in and a desk
        # with no policies must keep working exactly as before.
        from apps.service_desk.services.sla_service import SLAService

        SLAService.attach_to_ticket(ticket)

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

        from apps.service_desk.services.notification_service import (
            NotificationService,
        )

        NotificationService.notify_assignment(
            ticket,
            assignee=technician,
            actor=user,
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

        # ADR-010, Decision 3: the awaiting_confirmation → closed
        # transition requires the acting user to be the ticket's
        # requester (created_by). Enforced at the service layer so
        # it can't be bypassed through any view.
        if (
            current == "awaiting_confirmation"
            and status == "closed"
        ):
            if user is None or user != ticket.created_by:
                raise ValidationError(
                    "Only the requester can confirm and close this ticket."
                )

        ticket.status = status
        ticket.save(update_fields=["status", "updated_at"])

        # Record which event type to log
        if status == "closed" and current == "awaiting_confirmation":
            event_type = TicketHistory.EVENT_CONFIRMED
        else:
            event_type = TicketHistory.EVENT_STATUS_CHANGED

        TicketHistory.record(
            ticket=ticket,
            event_type=event_type,
            user=user,
            from_status=current,
            to_status=status,
        )

        from apps.service_desk.services.sla_service import SLAService

        SLAService.on_status_change(ticket, current, status)

        from apps.service_desk.services.notification_service import (
            NotificationService,
        )

        NotificationService.notify_status_change(
            ticket,
            from_status=current,
            to_status=status,
            actor=user,
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

        from apps.service_desk.services.sla_service import SLAService

        SLAService.recalculate(ticket)

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
    # Work Notes (internal — Technician/Manager only)
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_work_note(
        ticket: Ticket,
        note: str,
        user=None,
    ) -> TicketHistory:
        """
        Add an internal work note to a ticket.

        Work notes are never visible to Requesters — the detail
        template filters them out for users lacking
        service_desk.change_ticket (see ADR-010, Decision 3).
        """

        if not note.strip():
            raise ValidationError("Work note cannot be empty.")

        entry = TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_WORK_NOTE,
            user=user,
            comment=note.strip(),
        )

        # A work note is service-desk activity, so it stops the SLA
        # response clock (a requester comment does not).
        from apps.service_desk.services.sla_service import SLAService

        SLAService.mark_first_response(ticket)

        return entry

    # ==========================================================
    # Close
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def close_ticket(
        ticket: Ticket,
        user=None,
    ) -> Ticket:
        """
        Close a ticket after requester confirmation.

        Per ADR-010, Decision 3, a ticket must be in
        'awaiting_confirmation' status before it can be closed,
        and only the requester (created_by) may perform this
        action — enforced inside change_status().
        """

        if ticket.status != "awaiting_confirmation":
            raise ValidationError(
                "Only tickets awaiting requester confirmation "
                "can be closed."
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

    # ==========================================================
    # Attachments
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_attachment(
        ticket: Ticket,
        file,
        user=None,
        description: str = "",
    ):
        """
        Attach a file to a ticket.

        Validates the file extension against the allowlist and
        enforces the size cap (TicketAttachment constants).
        Records the upload in the ticket's audit trail using
        the existing EVENT_ATTACHMENT event type.
        """

        from apps.service_desk.models import TicketAttachment

        # Validate extension
        filename = getattr(file, "name", "")
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()
        else:
            ext = ""

        if ext not in TicketAttachment.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(TicketAttachment.ALLOWED_EXTENSIONS))
            raise ValidationError(
                f"File extension '.{ext}' is not allowed. "
                f"Allowed extensions: {allowed}"
            )

        # Validate size
        file.seek(0, 2)  # seek to end
        size = file.tell()
        file.seek(0)  # rewind

        if size > TicketAttachment.MAX_FILE_SIZE_BYTES:
            max_mb = TicketAttachment.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValidationError(
                f"File size exceeds the {max_mb} MB limit."
            )

        attachment = TicketAttachment.objects.create(
            ticket=ticket,
            file=file,
            description=description.strip(),
            uploaded_by=user,
            original_filename=filename,
            file_size=size,
        )

        TicketHistory.record(
            ticket=ticket,
            event_type=TicketHistory.EVENT_ATTACHMENT,
            user=user,
            comment=f"Attached: {filename}",
            metadata={
                "attachment_id": attachment.pk,
                "filename": filename,
                "size": size,
            },
        )

        return attachment