"""SLA evaluation and escalation engine."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.service_desk.models import Escalation, EscalationPolicy, Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SLAService:
    @staticmethod
    def attach_default_sla(ticket: Ticket) -> Ticket:
        """Bind SLA from request type or priority match."""
        if ticket.sla_id:
            ticket.apply_sla_deadlines()
            return ticket
        sla = None
        if ticket.request_type_id and ticket.request_type and ticket.request_type.sla_id:
            sla = ticket.request_type.sla
        elif ticket.priority_id and ticket.company_id:
            sla = (
                ticket.company.slas.filter(is_active=True, priority=ticket.priority)
                .order_by("resolution_minutes")
                .first()
            )
            if sla is None:
                sla = (
                    ticket.company.slas.filter(is_active=True, priority__isnull=True)
                    .order_by("resolution_minutes")
                    .first()
                )
        if sla:
            ticket.sla = sla
            ticket.apply_sla_deadlines()
        return ticket

    @classmethod
    def evaluate_ticket(cls, ticket: Ticket) -> dict:
        """Check breach state and fire escalations. Returns summary dict."""
        now = timezone.now()
        changes: list[str] = []
        update_fields: list[str] = []

        if (
            ticket.response_due_at
            and not ticket.first_response_at
            and now > ticket.response_due_at
            and not ticket.sla_response_breached
        ):
            ticket.sla_response_breached = True
            update_fields.append("sla_response_breached")
            changes.append("response_breached")
            NotificationService.notify_sla_breach(ticket, "response")
            AuditService.log(
                action="sla.response_breached",
                ticket=ticket,
                company=ticket.company,
                message="Response SLA breached",
            )

        if (
            ticket.resolution_due_at
            and not ticket.resolved_at
            and now > ticket.resolution_due_at
            and not ticket.sla_resolution_breached
        ):
            ticket.sla_resolution_breached = True
            update_fields.append("sla_resolution_breached")
            changes.append("resolution_breached")
            NotificationService.notify_sla_breach(ticket, "resolution")
            AuditService.log(
                action="sla.resolution_breached",
                ticket=ticket,
                company=ticket.company,
                message="Resolution SLA breached",
            )

        if update_fields:
            update_fields.append("updated_at")
            ticket.save(update_fields=update_fields)

        cls._maybe_escalate(ticket, now)
        return {"ticket_id": ticket.pk, "changes": changes}

    @classmethod
    def _maybe_escalate(cls, ticket: Ticket, now) -> Optional[Escalation]:
        if not ticket.sla_id or not ticket.resolution_due_at or ticket.resolved_at:
            return None
        created_at = ticket.created_at or now
        total = (ticket.resolution_due_at - created_at).total_seconds()
        if total <= 0:
            return None
        elapsed = (now - created_at).total_seconds()
        percent = (elapsed / total) * 100

        policies = (
            EscalationPolicy.objects.filter(sla=ticket.sla, is_active=True)
            .order_by("level")
        )
        for policy in policies:
            if percent < policy.trigger_after_percent:
                continue
            exists = ticket.escalations.filter(policy=policy, state=Escalation.State.OPEN).exists()
            if exists:
                continue
            with transaction.atomic():
                esc = Escalation.objects.create(
                    ticket=ticket,
                    sla=ticket.sla,
                    policy=policy,
                    level=policy.level,
                    reason=f"Auto-escalation at {percent:.0f}% of resolution SLA",
                )
                if policy.target_queue_id:
                    ticket.queue = policy.target_queue
                    ticket.save(update_fields=["queue", "updated_at"])
                for user in policy.notify_users.all():
                    NotificationService.create(
                        recipient=user,
                        subject=f"[{ticket.ticket_number}] Escalation L{policy.level}",
                        body=esc.reason,
                        ticket=ticket,
                        send_email=True,
                    )
                AuditService.log(
                    action="ticket.escalated",
                    ticket=ticket,
                    company=ticket.company,
                    message=esc.reason,
                    metadata={"level": policy.level},
                )
                return esc
        return None

    @classmethod
    def scan_open_tickets(cls, company_id: Optional[int] = None) -> int:
        qs = Ticket.objects.filter(resolved_at__isnull=True, closed_at__isnull=True)
        if company_id:
            qs = qs.filter(company_id=company_id)
        qs = qs.select_related("sla", "status", "queue", "company")
        count = 0
        for ticket in qs.iterator(chunk_size=200):
            result = cls.evaluate_ticket(ticket)
            if result["changes"]:
                count += 1
        logger.info("sla_scan processed_breaches=%s", count)
        return count

    @staticmethod
    def remaining_resolution(ticket: Ticket) -> Optional[timedelta]:
        if not ticket.resolution_due_at or ticket.resolved_at:
            return None
        return ticket.resolution_due_at - timezone.now()
