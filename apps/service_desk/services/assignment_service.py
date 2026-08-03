"""Ticket assignment and load-balanced routing."""

from __future__ import annotations

import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from apps.service_desk.models import AgentProfile, Queue, Ticket, TicketAssignment
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)
User = get_user_model()


class AssignmentService:
    @classmethod
    def assign(
        cls,
        ticket: Ticket,
        *,
        assignee=None,
        queue: Optional[Queue] = None,
        assigned_by=None,
        note: str = "",
    ) -> Ticket:
        if queue is not None:
            ticket.queue = queue
        if assignee is not None:
            ticket.assignee = assignee
        ticket.save()
        TicketAssignment.objects.filter(
            ticket=ticket, released_at__isnull=True
        ).update(released_at=timezone.now())
        TicketAssignment.objects.create(
            ticket=ticket,
            assignee=assignee,
            assigned_by=assigned_by,
            queue=queue or ticket.queue,
            note=note,
        )
        AuditService.log(
            action="ticket.assigned",
            ticket=ticket,
            company=ticket.company,
            actor=assigned_by,
            message=note or "Ticket assigned",
            metadata={
                "assignee_id": getattr(assignee, "pk", None),
                "queue_id": getattr(queue, "pk", None) or ticket.queue_id,
            },
        )
        return ticket

    @classmethod
    def auto_assign(cls, ticket: Ticket, assigned_by=None) -> Ticket:
        """Pick the least-loaded available agent in the ticket queue."""
        candidates = cls._candidates(ticket)
        if not candidates:
            logger.info("auto_assign no candidates ticket=%s", ticket.pk)
            return ticket
        return cls.assign(
            ticket,
            assignee=candidates[0],
            queue=ticket.queue,
            assigned_by=assigned_by,
            note="Auto-assigned by load balancer",
        )

    @staticmethod
    def _candidates(ticket: Ticket) -> list:
        open_filter = Q(assigned_tickets__closed_at__isnull=True) & Q(
            assigned_tickets__resolved_at__isnull=True
        )
        if ticket.queue_id:
            qs = ticket.queue.members.filter(is_active=True)
        elif ticket.company_id:
            agent_ids = AgentProfile.objects.filter(
                company=ticket.company, is_available=True
            ).values_list("user_id", flat=True)
            qs = User.objects.filter(pk__in=agent_ids, is_active=True)
        else:
            qs = User.objects.filter(is_staff=True, is_active=True)

        qs = qs.annotate(open_count=Count("assigned_tickets", filter=open_filter))
        # Honour max_open_tickets when profile exists
        ranked = []
        for user in qs.order_by("open_count", "id"):
            profile = getattr(user, "agent_profile", None)
            if profile and not profile.is_available:
                continue
            if profile and user.open_count >= profile.max_open_tickets:
                continue
            ranked.append(user)
        return ranked
