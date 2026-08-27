from apps.service_desk.models import ChangeRequest, CABDecision
from apps.service_desk.models.ticket_history import TicketHistory
from apps.service_desk.security.policies import (
    is_administrator,
    is_manager,
)


def _require_manager_or_administrator(user):
    if not (is_administrator(user) or is_manager(user)):
        raise PermissionError("Change Management requires Manager or Administrator access.")


def _transition(user, change, new_status, comment):
    _require_manager_or_administrator(user)

    old_status = change.status

    change.status = new_status
    change.save(update_fields=["status", "updated_at"])

    TicketHistory.record(
        ticket=change.ticket,
        event_type=TicketHistory.EVENT_UPDATED,
        user=user,
        old_value=old_status,
        new_value=new_status,
        comment=comment,
        metadata={
            "change_request_id": change.pk,
            "change_request_status_transition": True,
        },
    )

    return change


def submit_change(user, change):
    if change.status != ChangeRequest.Status.DRAFT:
        raise ValueError("Only draft changes can be submitted.")
    return _transition(user, change, ChangeRequest.Status.SUBMITTED, "Change submitted.")


def approve_change(user, change, notes=""):
    if change.status != ChangeRequest.Status.SUBMITTED:
        raise ValueError("Only submitted changes can be approved.")

    _require_manager_or_administrator(user)

    decision = CABDecision.objects.create(
        change=change,
        approver=user,
        decision=CABDecision.Decision.APPROVED,
        notes=notes,
    )

    _transition(user, change, ChangeRequest.Status.APPROVED, "Change approved.")
    return decision


def reject_change(user, change, notes=""):
    if change.status != ChangeRequest.Status.SUBMITTED:
        raise ValueError("Only submitted changes can be rejected.")

    _require_manager_or_administrator(user)

    decision = CABDecision.objects.create(
        change=change,
        approver=user,
        decision=CABDecision.Decision.REJECTED,
        notes=notes,
    )

    _transition(user, change, ChangeRequest.Status.REJECTED, "Change rejected.")
    return decision


def schedule_change(user, change):
    if change.status != ChangeRequest.Status.APPROVED:
        raise ValueError("Only approved changes can be scheduled.")
    return _transition(user, change, ChangeRequest.Status.SCHEDULED, "Change scheduled.")


def implement_change(user, change):
    if change.status != ChangeRequest.Status.SCHEDULED:
        raise ValueError("Only scheduled changes can be implemented.")
    return _transition(user, change, ChangeRequest.Status.IMPLEMENTED, "Change implemented.")


def close_change(user, change):
    if change.status != ChangeRequest.Status.IMPLEMENTED:
        raise ValueError("Only implemented changes can be closed.")
    return _transition(user, change, ChangeRequest.Status.CLOSED, "Change closed.")


def cancel_change(user, change):
    if change.status in {
        ChangeRequest.Status.CLOSED,
        ChangeRequest.Status.CANCELLED,
    }:
        raise ValueError("Closed or cancelled changes cannot be cancelled.")
    return _transition(user, change, ChangeRequest.Status.CANCELLED, "Change cancelled.")