"""Approval workflow helpers."""

from __future__ import annotations

from django.utils import timezone

from apps.service_desk.models import ApprovalRequest, Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService


class ApprovalService:
    @staticmethod
    def request_approval(ticket: Ticket, approver, requested_by=None, reason: str = ""):
        req = ApprovalRequest.objects.create(
            ticket=ticket,
            approver=approver,
            requested_by=requested_by,
            reason=reason,
        )
        NotificationService.create(
            recipient=approver,
            subject=f"[{ticket.ticket_number}] Approval required",
            body=reason or f"Please approve {ticket.ticket_number}",
            ticket=ticket,
            send_email=True,
        )
        AuditService.log(
            action="approval.requested",
            ticket=ticket,
            company=ticket.company,
            actor=requested_by,
            message=reason,
        )
        return req

    @staticmethod
    def decide(request_obj: ApprovalRequest, *, approved: bool, actor=None, note: str = ""):
        request_obj.state = (
            ApprovalRequest.State.APPROVED
            if approved
            else ApprovalRequest.State.REJECTED
        )
        request_obj.decision_note = note
        request_obj.decided_at = timezone.now()
        request_obj.save()
        AuditService.log(
            action="approval.decided",
            ticket=request_obj.ticket,
            company=request_obj.ticket.company,
            actor=actor,
            message=note,
            metadata={"approved": approved},
        )
        return request_obj
