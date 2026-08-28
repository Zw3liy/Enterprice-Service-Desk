from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import CatalogItem, RequestType, ServiceRequest, ServiceRequestHistory

User = get_user_model()


class ServiceRequestService:
    """
    Service Request business service.

    A ``ServiceRequest`` always wraps exactly one ``Ticket`` — created
    through ``TicketService.create_ticket`` and mutated through
    ``TicketService`` for every concern the ticket already owns
    (assignment, status, comments, attachments, SLA, notifications).
    This service owns only the catalogue-specific state layered on
    top: approval, fulfilment staging, cancellation. See ADR-011,
    Decision 2.
    """

    STATUS_FLOW = {
        ServiceRequest.STATUS_PENDING_APPROVAL: [
            ServiceRequest.STATUS_APPROVED,
            ServiceRequest.STATUS_REJECTED,
            ServiceRequest.STATUS_CANCELLED,
        ],
        ServiceRequest.STATUS_APPROVED: [
            ServiceRequest.STATUS_ASSIGNED,
            ServiceRequest.STATUS_CANCELLED,
        ],
        ServiceRequest.STATUS_ASSIGNED: [
            ServiceRequest.STATUS_FULFILLING,
            ServiceRequest.STATUS_CANCELLED,
        ],
        ServiceRequest.STATUS_FULFILLING: [
            ServiceRequest.STATUS_FULFILLED,
            ServiceRequest.STATUS_CANCELLED,
        ],
        ServiceRequest.STATUS_REJECTED: [],
        ServiceRequest.STATUS_FULFILLED: [],
        ServiceRequest.STATUS_CANCELLED: [],
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_request(
        catalog_item: CatalogItem,
        user,
        quantity: int = 1,
        justification: str = "",
    ) -> ServiceRequest:

        if not catalog_item.is_active:
            raise ValidationError(
                "This catalogue item is no longer available."
            )

        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

        from apps.service_desk.services.ticket_service import TicketService

        request_type = RequestType.objects.filter(
            name="Service Request"
        ).first()

        ticket = TicketService.create_ticket(
            title=f"Service Request: {catalog_item.name}",
            description=justification.strip() or catalog_item.description,
            department=catalog_item.fulfillment_department,
            request_type=request_type,
            priority=catalog_item.default_priority,
            created_by=user,
        )

        status = (
            ServiceRequest.STATUS_PENDING_APPROVAL
            if catalog_item.requires_approval
            else ServiceRequest.STATUS_APPROVED
        )

        expected_fulfillment_date = None
        if catalog_item.expected_delivery_days is not None:
            expected_fulfillment_date = (
                datetime.date.today()
                + datetime.timedelta(days=catalog_item.expected_delivery_days)
            )

        service_request = ServiceRequest.objects.create(
            ticket=ticket,
            catalog_item=catalog_item,
            quantity=quantity,
            justification=justification.strip(),
            status=status,
            expected_fulfillment_date=expected_fulfillment_date,
        )

        ServiceRequestHistory.record(
            service_request=service_request,
            event_type=ServiceRequestHistory.EVENT_CREATED,
            user=user,
            new_value=status,
            comment=f"Requested {catalog_item.name}.",
        )

        return service_request

    # ==========================================================
    # Internal transition helper
    # ==========================================================

    @staticmethod
    def _transition(
        service_request: ServiceRequest,
        new_status: str,
        event_type: str,
        user=None,
        comment: str = "",
    ) -> ServiceRequest:

        current = service_request.status
        allowed = ServiceRequestService.STATUS_FLOW.get(current, [])

        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move a service request from {current} "
                f"to {new_status}."
            )

        service_request.status = new_status
        service_request.save(update_fields=["status", "updated_at"])

        ServiceRequestHistory.record(
            service_request=service_request,
            event_type=event_type,
            user=user,
            old_value=current,
            new_value=new_status,
            comment=comment,
        )

        return service_request

    # ==========================================================
    # Approval
    # ==========================================================

    @staticmethod
    def _assert_may_decide(approver) -> None:
        """
        Only a Manager or an Administrator may decide an approval.

        Enforced here, not only via the change_servicerequest
        permission a Technician also holds (for assignment/fulfilment
        purposes) — separation of duties for approval specifically
        must not be bypassable just because a caller holds the
        broader workflow-change permission.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if approver is None or not (
            is_administrator(approver) or is_manager(approver)
        ):
            raise ValidationError(
                "Only a manager or an administrator can approve or "
                "reject a service request."
            )

    @staticmethod
    @transaction.atomic
    def approve_request(
        service_request: ServiceRequest,
        approver,
        comment: str = "",
    ) -> ServiceRequest:

        if service_request.status != ServiceRequest.STATUS_PENDING_APPROVAL:
            raise ValidationError(
                "Only a request pending approval can be approved."
            )

        ServiceRequestService._assert_may_decide(approver)

        requester = service_request.ticket.created_by
        if requester is not None and approver is not None and requester.pk == approver.pk:
            raise ValidationError(
                "You cannot approve your own service request."
            )

        from apps.service_desk.models import ServiceRequestApproval

        ServiceRequestApproval.objects.create(
            service_request=service_request,
            actor=approver,
            decision=ServiceRequestApproval.DECISION_APPROVED,
            comment=comment.strip(),
        )

        ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_APPROVED,
            ServiceRequestHistory.EVENT_APPROVED,
            user=approver,
            comment=comment.strip(),
        )

        from apps.service_desk.models import Notification
        from apps.service_desk.services.notification_service import (
            NotificationService,
        )

        NotificationService.notify(
            recipient=requester,
            kind=Notification.KIND_SERVICE_REQUEST_APPROVED,
            subject=f"Your request for {service_request.catalog_item.name} was approved",
            body=comment.strip(),
            ticket=service_request.ticket,
            actor=approver,
        )

        return service_request

    @staticmethod
    @transaction.atomic
    def reject_request(
        service_request: ServiceRequest,
        approver,
        comment: str,
    ) -> ServiceRequest:

        if service_request.status != ServiceRequest.STATUS_PENDING_APPROVAL:
            raise ValidationError(
                "Only a request pending approval can be rejected."
            )

        if not comment.strip():
            raise ValidationError(
                "A reason is required when rejecting a service request."
            )

        ServiceRequestService._assert_may_decide(approver)

        requester = service_request.ticket.created_by
        if requester is not None and approver is not None and requester.pk == approver.pk:
            raise ValidationError(
                "You cannot reject your own service request."
            )

        from apps.service_desk.models import ServiceRequestApproval

        ServiceRequestApproval.objects.create(
            service_request=service_request,
            actor=approver,
            decision=ServiceRequestApproval.DECISION_REJECTED,
            comment=comment.strip(),
        )

        ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_REJECTED,
            ServiceRequestHistory.EVENT_REJECTED,
            user=approver,
            comment=comment.strip(),
        )

        from apps.service_desk.models import Notification
        from apps.service_desk.services.notification_service import (
            NotificationService,
        )

        NotificationService.notify(
            recipient=requester,
            kind=Notification.KIND_SERVICE_REQUEST_REJECTED,
            subject=f"Your request for {service_request.catalog_item.name} was rejected",
            body=comment.strip(),
            ticket=service_request.ticket,
            actor=approver,
        )

        return service_request

    # ==========================================================
    # Assignment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def assign_request(
        service_request: ServiceRequest,
        technician,
        user=None,
    ) -> ServiceRequest:

        if service_request.status != ServiceRequest.STATUS_APPROVED:
            raise ValidationError(
                "Only an approved request can be assigned."
            )

        from apps.service_desk.services.ticket_service import TicketService

        ticket = service_request.ticket

        TicketService.assign_ticket(ticket, technician, user=user)

        if ticket.status == "open":
            TicketService.change_status(ticket, "in_progress", user=user)

        return ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_ASSIGNED,
            ServiceRequestHistory.EVENT_ASSIGNED,
            user=user,
            comment=f"Assigned to {technician.get_username()}.",
        )

    # ==========================================================
    # Fulfilment
    # ==========================================================

    @staticmethod
    def _assert_may_fulfil(service_request: ServiceRequest, user) -> None:
        """
        Only the ticket's assignee, a manager or an administrator may
        advance fulfilment — enforced here so it cannot be bypassed
        by any future call site that only checks change_servicerequest.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None:
            raise ValidationError("An acting user is required.")

        if is_administrator(user) or is_manager(user):
            return

        assignee = service_request.ticket.assigned_to
        if assignee is None or assignee.pk != user.pk:
            raise ValidationError(
                "Only the assigned technician can update fulfilment."
            )

    @staticmethod
    @transaction.atomic
    def mark_fulfilling(
        service_request: ServiceRequest,
        user=None,
    ) -> ServiceRequest:

        if service_request.status != ServiceRequest.STATUS_ASSIGNED:
            raise ValidationError(
                "Only an assigned request can move to fulfilling."
            )

        ServiceRequestService._assert_may_fulfil(service_request, user)

        return ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_FULFILLING,
            ServiceRequestHistory.EVENT_FULFILLING,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def mark_fulfilled(
        service_request: ServiceRequest,
        user=None,
    ) -> ServiceRequest:

        if service_request.status != ServiceRequest.STATUS_FULFILLING:
            raise ValidationError(
                "Only a request being fulfilled can be marked fulfilled."
            )

        ServiceRequestService._assert_may_fulfil(service_request, user)

        from apps.service_desk.services.ticket_service import TicketService

        ticket = service_request.ticket
        if ticket.status in ("in_progress", "pending"):
            TicketService.change_status(ticket, "resolved", user=user)

        result = ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_FULFILLED,
            ServiceRequestHistory.EVENT_FULFILLED,
            user=user,
        )

        from apps.service_desk.models import Notification
        from apps.service_desk.services.notification_service import (
            NotificationService,
        )

        NotificationService.notify(
            recipient=ticket.created_by,
            kind=Notification.KIND_SERVICE_REQUEST_FULFILLED,
            subject=f"Your request for {service_request.catalog_item.name} was fulfilled",
            body=(
                "Please confirm the ticket once you have reviewed it "
                "so it can be closed."
            ),
            ticket=ticket,
            actor=user,
        )

        return result

    # ==========================================================
    # Cancellation
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def cancel_request(
        service_request: ServiceRequest,
        user,
        reason: str = "",
    ) -> ServiceRequest:

        if not service_request.is_open:
            raise ValidationError(
                "This request can no longer be cancelled."
            )

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        requester = service_request.ticket.created_by
        is_requester = (
            user is not None
            and requester is not None
            and user.pk == requester.pk
        )

        if not (is_requester or is_administrator(user) or is_manager(user)):
            raise ValidationError(
                "Only the requester, a manager or an administrator "
                "can cancel this request."
            )

        result = ServiceRequestService._transition(
            service_request,
            ServiceRequest.STATUS_CANCELLED,
            ServiceRequestHistory.EVENT_CANCELLED,
            user=user,
            comment=reason.strip(),
        )

        if reason.strip():
            from apps.service_desk.services.ticket_service import TicketService

            TicketService.add_comment(
                service_request.ticket,
                f"Service request cancelled: {reason.strip()}",
                user=user,
            )

        return result
