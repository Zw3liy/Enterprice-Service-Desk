"""Approval engine services."""

from __future__ import annotations

from apps.approval_engine.models import ApprovalPolicy
from apps.change_management.services import ChangeService
from apps.service_desk.models import ApprovalRequest, Ticket
from apps.service_desk.workflow.approvals import ApprovalService

__all__ = ["ApprovalService", "ChangeService", "ApprovalEngine"]


class ApprovalEngine:
    @staticmethod
    def ensure_default_policies(company) -> list[ApprovalPolicy]:
        defaults = [
            ("change-normal", "Normal change approval", "change", {"change_type": "normal"}),
            ("purchase-over-10k", "Purchase over 10k", "purchase_request", {"min_total": 10000}),
        ]
        out = []
        for code, name, entity, conditions in defaults:
            obj, _ = ApprovalPolicy.objects.get_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "entity_type": entity,
                    "conditions": conditions,
                    "min_approvers": 1,
                    "is_active": True,
                },
            )
            out.append(obj)
        return out

    @staticmethod
    def request_ticket_approval(ticket: Ticket, approver, requested_by=None, reason: str = ""):
        return ApprovalService.request_approval(
            ticket,
            approver=approver,
            requested_by=requested_by,
            reason=reason,
        )

    @staticmethod
    def pending_for(user):
        return ApprovalRequest.objects.filter(
            approver=user, state=ApprovalRequest.State.PENDING
        ).select_related("ticket")
