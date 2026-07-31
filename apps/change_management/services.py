"""Change management application services."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.change_management.models import CABMeeting, ChangeApproval, ChangeRequest
from apps.service_desk.models import Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.workflow.approvals import ApprovalService

logger = logging.getLogger(__name__)


class ChangeService:
    @classmethod
    @transaction.atomic
    def create_change(cls, **kwargs) -> Ticket:
        change_type = kwargs.pop("change_type", ChangeRequest.ChangeType.NORMAL)
        risk = kwargs.pop("risk", ChangeRequest.Risk.MEDIUM)
        justification = kwargs.pop("justification", "")
        implementation_plan = kwargs.pop("implementation_plan", "")
        rollback_plan = kwargs.pop("rollback_plan", "")
        test_plan = kwargs.pop("test_plan", "")
        scheduled_start = kwargs.pop("scheduled_start", None)
        scheduled_end = kwargs.pop("scheduled_end", None)
        kwargs.setdefault("ticket_type", Ticket.TicketType.CHANGE)
        ticket = TicketService.create_ticket(**kwargs)
        cab_required = change_type != ChangeRequest.ChangeType.STANDARD
        ChangeRequest.objects.create(
            ticket=ticket,
            company=ticket.company,
            change_type=change_type,
            risk=risk,
            justification=justification,
            implementation_plan=implementation_plan,
            rollback_plan=rollback_plan,
            test_plan=test_plan,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            cab_required=cab_required,
            requester=kwargs.get("actor") or kwargs.get("requester_user"),
            state=ChangeRequest.State.DRAFT,
        )
        return ticket

    @staticmethod
    def open_changes(company=None):
        return TicketService.search(
            company=company,
            ticket_type=Ticket.TicketType.CHANGE,
            open_only=True,
        )

    @classmethod
    def submit(cls, ticket: Ticket, actor=None) -> ChangeRequest:
        change = ticket.change_request
        change.state = (
            ChangeRequest.State.CAB_REVIEW
            if change.cab_required
            else ChangeRequest.State.APPROVED
        )
        if not change.cab_required:
            change.state = ChangeRequest.State.APPROVED
        else:
            change.state = ChangeRequest.State.SUBMITTED
        change.save(update_fields=["state", "updated_at"])
        AuditService.log(
            action="change.submitted",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message=f"Change submitted ({change.change_type})",
        )
        return change

    @classmethod
    def request_cab_approval(
        cls, change_ticket: Ticket, approver, requested_by=None, reason: str = ""
    ):
        change = change_ticket.change_request
        change.state = ChangeRequest.State.CAB_REVIEW
        change.save(update_fields=["state", "updated_at"])
        ChangeApproval.objects.get_or_create(
            change=change, approver=approver, defaults={"decision": ChangeApproval.Decision.PENDING}
        )
        ApprovalService.request_approval(
            change_ticket,
            approver=approver,
            requested_by=requested_by,
            reason=reason or "CAB approval required",
        )
        NotificationService.create(
            recipient=approver,
            subject=f"[{change_ticket.ticket_number}] CAB approval required",
            body=reason or change.justification or change_ticket.title,
            ticket=change_ticket,
            send_email=True,
        )
        return change

    @classmethod
    @transaction.atomic
    def decide(
        cls,
        change_ticket: Ticket,
        *,
        approver,
        approved: bool,
        comment: str = "",
    ) -> ChangeApproval:
        change = change_ticket.change_request
        approval, _ = ChangeApproval.objects.get_or_create(
            change=change, approver=approver
        )
        approval.decision = (
            ChangeApproval.Decision.APPROVED
            if approved
            else ChangeApproval.Decision.REJECTED
        )
        approval.comment = comment
        approval.decided_at = timezone.now()
        approval.save()
        if approved:
            pending = change.approvals.filter(decision=ChangeApproval.Decision.PENDING).exists()
            if not pending:
                change.state = ChangeRequest.State.APPROVED
                change.save(update_fields=["state", "updated_at"])
        else:
            change.state = ChangeRequest.State.REJECTED
            change.save(update_fields=["state", "updated_at"])
        AuditService.log(
            action="change.decision",
            ticket=change_ticket,
            company=change_ticket.company,
            actor=approver,
            message=comment,
            metadata={"approved": approved},
        )
        return approval

    @classmethod
    def schedule(cls, ticket: Ticket, start, end, actor=None) -> ChangeRequest:
        change = ticket.change_request
        change.scheduled_start = start
        change.scheduled_end = end
        change.state = ChangeRequest.State.SCHEDULED
        change.save()
        AuditService.log(
            action="change.scheduled",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message=f"Scheduled {start} → {end}",
        )
        return change

    @classmethod
    def start_implementation(cls, ticket: Ticket, actor=None) -> ChangeRequest:
        change = ticket.change_request
        change.state = ChangeRequest.State.IMPLEMENTING
        change.actual_start = timezone.now()
        change.save()
        return change

    @classmethod
    def complete(cls, ticket: Ticket, *, success: bool = True, actor=None) -> ChangeRequest:
        change = ticket.change_request
        change.state = (
            ChangeRequest.State.COMPLETED if success else ChangeRequest.State.FAILED
        )
        change.actual_end = timezone.now()
        change.save()
        AuditService.log(
            action="change.completed" if success else "change.failed",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message=change.state,
        )
        return change

    @staticmethod
    def create_cab_meeting(company, title, scheduled_at, chair=None, members=None):
        meeting = CABMeeting.objects.create(
            company=company,
            title=title,
            scheduled_at=scheduled_at,
            chair=chair,
        )
        if members:
            meeting.members.set(members)
        return meeting