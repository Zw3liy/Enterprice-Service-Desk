"""Ticket application service — orchestrates create/update lifecycle."""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet

from apps.service_desk.dynamic_validation import validate_custom_fields
from apps.service_desk.models import (
    Status,
    Ticket,
    TicketAttachment,
    TicketComment,
    WorkLog,
)
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.services.assignment_service import AssignmentService
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.sla_service import SLAService

logger = logging.getLogger(__name__)
User = get_user_model()


class TicketService:
    @staticmethod
    def base_queryset() -> QuerySet[Ticket]:
        return (
            Ticket.objects.select_related(
                "company",
                "department",
                "request_type",
                "category",
                "priority",
                "status",
                "queue",
                "sla",
                "requester",
                "requester_user",
                "assignee",
                "parent",
            )
            .prefetch_related(
                "assets",
                Prefetch(
                    "comments",
                    queryset=TicketComment.objects.select_related("author").order_by(
                        "created_at"
                    ),
                ),
            )
        )

    @classmethod
    def get_ticket(cls, ticket_id: int | str) -> Ticket:
        qs = cls.base_queryset()
        if isinstance(ticket_id, str) and not ticket_id.isdigit():
            return qs.get(Q(ticket_number=ticket_id) | Q(uuid=ticket_id))
        return qs.get(pk=ticket_id)

    @classmethod
    @transaction.atomic
    def create_ticket(
        cls,
        *,
        title: str,
        description: str = "",
        company=None,
        department=None,
        request_type=None,
        category=None,
        priority=None,
        status=None,
        queue=None,
        sla=None,
        requester=None,
        requester_user=None,
        assignee=None,
        ticket_type: str = Ticket.TicketType.INCIDENT,
        channel: str = Ticket.Channel.PORTAL,
        custom_field_values: Optional[dict] = None,
        tags: Optional[list] = None,
        assets=None,
        impact: int = 3,
        urgency: int = 3,
        actor=None,
        auto_assign: bool = False,
        run_ai: bool = True,
    ) -> Ticket:
        custom_field_values = custom_field_values or {}
        if request_type is not None:
            errors = validate_custom_fields(request_type, custom_field_values)
            if errors:
                raise ValidationError(errors)
            if department is None:
                department = request_type.department
            if company is None and department is not None:
                company = department.company
            if priority is None and request_type.default_priority_id:
                priority = request_type.default_priority
            if queue is None and request_type.default_queue_id:
                queue = request_type.default_queue
            if sla is None and request_type.sla_id:
                sla = request_type.sla

        if status is None and company is not None:
            status = (
                Status.objects.filter(
                    company=company, code="new", is_active=True
                ).first()
                or Status.objects.filter(company=company, is_active=True)
                .order_by("rank")
                .first()
            )

        ticket = Ticket(
            title=title.strip(),
            description=description.strip(),
            company=company,
            department=department,
            request_type=request_type,
            category=category,
            priority=priority,
            status=status,
            queue=queue,
            sla=sla,
            requester=requester,
            requester_user=requester_user or actor,
            assignee=assignee,
            ticket_type=ticket_type,
            channel=channel,
            custom_field_values=custom_field_values,
            tags=tags or [],
            impact=impact,
            urgency=urgency,
        )
        ticket = SLAService.attach_default_sla(ticket)
        ticket.save()

        if assets:
            ticket.assets.set(assets)

        if run_ai:
            AIService.enrich_ticket(ticket)

        if auto_assign and not ticket.assignee_id:
            AssignmentService.auto_assign(ticket, assigned_by=actor)

        # Ensure SLA deadlines after created_at exists
        if ticket.sla_id and not ticket.response_due_at:
            ticket.apply_sla_deadlines()
            ticket.save(update_fields=["response_due_at", "resolution_due_at", "updated_at"])

        logger.info("ticket_created number=%s id=%s", ticket.ticket_number, ticket.pk)
        return ticket

    @classmethod
    @transaction.atomic
    def update_ticket(
        cls,
        ticket: Ticket,
        *,
        actor=None,
        **fields: Any,
    ) -> Ticket:
        allowed = {
            "title",
            "description",
            "category",
            "priority",
            "status",
            "queue",
            "sla",
            "assignee",
            "department",
            "request_type",
            "ticket_type",
            "channel",
            "custom_field_values",
            "tags",
            "impact",
            "urgency",
            "is_major_incident",
            "parent",
        }
        status = fields.get("status", ticket.status)
        for key, value in fields.items():
            if key not in allowed:
                continue
            setattr(ticket, key, value)

        if status is not None and status != ticket.status:
            ticket.status = status

        if ticket.status_id and ticket.status:
            if ticket.status.category == Status.CategoryChoice.RESOLVED and not ticket.resolved_at:
                ticket.mark_resolved()
            if ticket.status.category == Status.CategoryChoice.CLOSED and not ticket.closed_at:
                ticket.mark_closed()

        if ticket.request_type_id and ticket.custom_field_values:
            errors = validate_custom_fields(ticket.request_type, ticket.custom_field_values)
            if errors:
                raise ValidationError(errors)

        ticket.save()
        AuditService.log(
            action="ticket.updated",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message="Ticket updated",
            metadata={k: str(v) for k, v in fields.items() if k in allowed},
        )
        return ticket

    @classmethod
    @transaction.atomic
    def add_comment(
        cls,
        ticket: Ticket,
        *,
        body: str,
        author=None,
        is_internal: bool = False,
        is_system: bool = False,
    ) -> TicketComment:
        body = (body or "").strip()
        if not body:
            raise ValidationError({"body": "Comment body is required."})
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=author,
            body=body,
            is_internal=is_internal,
            is_system=is_system,
        )
        return comment

    @classmethod
    @transaction.atomic
    def add_work_log(
        cls,
        ticket: Ticket,
        *,
        description: str,
        minutes_spent: int,
        author=None,
        is_billable: bool = False,
    ) -> WorkLog:
        if minutes_spent <= 0:
            raise ValidationError({"minutes_spent": "Must be positive."})
        return WorkLog.objects.create(
            ticket=ticket,
            author=author,
            description=description.strip(),
            minutes_spent=minutes_spent,
            is_billable=is_billable,
        )

    @classmethod
    def add_attachment(
        cls,
        ticket: Ticket,
        *,
        uploaded_file,
        uploaded_by=None,
        comment: Optional[TicketComment] = None,
    ) -> TicketAttachment:
        attachment = TicketAttachment(
            ticket=ticket,
            comment=comment,
            file=uploaded_file,
            original_name=getattr(uploaded_file, "name", "file")[:255],
            content_type=getattr(uploaded_file, "content_type", "") or "",
            size_bytes=getattr(uploaded_file, "size", 0) or 0,
            uploaded_by=uploaded_by,
        )
        attachment.save()
        return attachment

    @classmethod
    def search(
        cls,
        *,
        company=None,
        query: str = "",
        status_id=None,
        priority_id=None,
        queue_id=None,
        assignee_id=None,
        ticket_type: str = "",
        open_only: bool = False,
        mine_user=None,
    ) -> QuerySet[Ticket]:
        qs = cls.base_queryset()
        if company is not None:
            qs = qs.filter(company=company)
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(ticket_number__icontains=query)
                | Q(tags__icontains=query)
            )
        if status_id:
            qs = qs.filter(status_id=status_id)
        if priority_id:
            qs = qs.filter(priority_id=priority_id)
        if queue_id:
            qs = qs.filter(queue_id=queue_id)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if ticket_type:
            qs = qs.filter(ticket_type=ticket_type)
        if open_only:
            qs = qs.filter(closed_at__isnull=True).filter(
                Q(status__isnull=True) | Q(status__is_terminal=False)
            )
        if mine_user is not None:
            qs = qs.filter(Q(assignee=mine_user) | Q(requester_user=mine_user))
        return qs
