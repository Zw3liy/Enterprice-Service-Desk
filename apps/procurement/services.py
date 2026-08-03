"""Procurement application services."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import StockMovement
from apps.inventory.services import InventoryService
from apps.procurement.models import PurchaseOrder, PurchaseRequest, PurchaseRequestLine
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.workflow.approvals import ApprovalService

logger = logging.getLogger(__name__)


class ProcurementService:
    @classmethod
    @transaction.atomic
    def create_request(
        cls,
        company,
        *,
        title: str,
        justification: str = "",
        requester=None,
        lines: list[dict] | None = None,
        needed_by=None,
        currency: str = "ZAR",
    ) -> PurchaseRequest:
        pr = PurchaseRequest.objects.create(
            company=company,
            title=title,
            justification=justification,
            requester=requester,
            needed_by=needed_by,
            currency=currency,
            state=PurchaseRequest.State.DRAFT,
        )
        total = Decimal("0")
        for line in lines or []:
            obj = PurchaseRequestLine.objects.create(
                request=pr,
                description=line.get("description") or "Item",
                quantity=int(line.get("quantity") or 1),
                unit_price=Decimal(str(line.get("unit_price") or "0")),
                sku=line.get("sku") or "",
            )
            total += obj.line_total
        pr.total_estimate = total
        pr.save(update_fields=["total_estimate", "updated_at"])
        AuditService.log(
            action="procurement.request_created",
            company=company,
            actor=requester,
            message=pr.number,
            object_type="purchase_request",
            object_id=str(pr.pk),
        )
        return pr

    @classmethod
    def submit(cls, pr: PurchaseRequest, actor=None) -> PurchaseRequest:
        pr.state = PurchaseRequest.State.SUBMITTED
        pr.save(update_fields=["state", "updated_at"])
        AuditService.log(
            action="procurement.request_submitted",
            company=pr.company,
            actor=actor,
            message=pr.number,
            object_type="purchase_request",
            object_id=str(pr.pk),
        )
        return pr

    @classmethod
    def request_approval(cls, pr: PurchaseRequest, approver, actor=None) -> PurchaseRequest:
        pr.approver = approver
        pr.save(update_fields=["approver", "updated_at"])
        # Use ticket-less approval path via notification only if no ticket;
        # create lightweight audit.
        AuditService.log(
            action="procurement.approval_requested",
            company=pr.company,
            actor=actor,
            message=f"{pr.number} → {getattr(approver, 'username', approver)}",
            object_type="purchase_request",
            object_id=str(pr.pk),
        )
        return pr

    @classmethod
    def decide(cls, pr: PurchaseRequest, *, approved: bool, actor=None, note: str = "") -> PurchaseRequest:
        pr.state = (
            PurchaseRequest.State.APPROVED if approved else PurchaseRequest.State.REJECTED
        )
        pr.approver = actor
        pr.save(update_fields=["state", "approver", "updated_at"])
        AuditService.log(
            action="procurement.decided",
            company=pr.company,
            actor=actor,
            message=note or pr.state,
            object_type="purchase_request",
            object_id=str(pr.pk),
            metadata={"approved": approved},
        )
        return pr

    @classmethod
    @transaction.atomic
    def create_po_from_request(
        cls, pr: PurchaseRequest, *, vendor=None, user=None
    ) -> PurchaseOrder:
        if pr.state != PurchaseRequest.State.APPROVED:
            raise ValueError("Purchase request must be approved")
        po = PurchaseOrder.objects.create(
            company=pr.company,
            purchase_request=pr,
            vendor=vendor,
            currency=pr.currency,
            total=pr.total_estimate,
            state=PurchaseOrder.State.DRAFT,
            created_by=user,
        )
        pr.state = PurchaseRequest.State.ORDERED
        pr.save(update_fields=["state", "updated_at"])
        return po

    @classmethod
    def send_po(cls, po: PurchaseOrder, actor=None) -> PurchaseOrder:
        po.state = PurchaseOrder.State.SENT
        po.ordered_at = timezone.now()
        po.save(update_fields=["state", "ordered_at", "updated_at"])
        AuditService.log(
            action="procurement.po_sent",
            company=po.company,
            actor=actor,
            message=po.number,
            object_type="purchase_order",
            object_id=str(po.pk),
        )
        return po

    @classmethod
    @transaction.atomic
    def receive_po(
        cls,
        po: PurchaseOrder,
        *,
        warehouse=None,
        actor=None,
        receive_to_inventory: bool = True,
    ) -> PurchaseOrder:
        po.state = PurchaseOrder.State.RECEIVED
        po.save(update_fields=["state", "updated_at"])
        if receive_to_inventory and po.purchase_request_id:
            wh = warehouse or InventoryService.ensure_warehouse(po.company)
            for line in po.purchase_request.lines.all():
                sku = line.sku or f"PR-{line.pk}"
                item = InventoryService.upsert_item(
                    po.company, sku=sku, name=line.description
                )
                InventoryService.move(
                    company=po.company,
                    warehouse=wh,
                    item=item,
                    movement_type=StockMovement.MovementType.RECEIPT,
                    quantity=line.quantity,
                    reference=po.number,
                    notes=f"Received from {po.number}",
                    user=actor,
                )
        AuditService.log(
            action="procurement.po_received",
            company=po.company,
            actor=actor,
            message=po.number,
            object_type="purchase_order",
            object_id=str(po.pk),
        )
        return po
