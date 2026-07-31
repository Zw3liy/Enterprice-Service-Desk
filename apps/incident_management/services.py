"""Incident management application services."""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.incident_management.models import IncidentTimelineEvent, MajorIncident
from apps.service_desk.models import Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService
from apps.service_desk.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class IncidentService:
    @staticmethod
    def create_incident(**kwargs) -> Ticket:
        kwargs.setdefault("ticket_type", Ticket.TicketType.INCIDENT)
        return TicketService.create_ticket(**kwargs)

    @staticmethod
    def open_incidents(company=None):
        return TicketService.search(
            company=company,
            ticket_type=Ticket.TicketType.INCIDENT,
            open_only=True,
        )

    @classmethod
    @transaction.atomic
    def declare_major(
        cls,
        ticket: Ticket,
        *,
        severity: str = MajorIncident.Severity.SEV1,
        commander=None,
        customer_impact: str = "",
        bridge_channel: str = "",
        actor=None,
    ) -> MajorIncident:
        ticket.is_major_incident = True
        ticket.save(update_fields=["is_major_incident", "updated_at"])
        record, _ = MajorIncident.objects.update_or_create(
            ticket=ticket,
            defaults={
                "company": ticket.company,
                "severity": severity,
                "commander": commander,
                "customer_impact": customer_impact,
                "bridge_channel": bridge_channel,
            },
        )
        cls.add_timeline(
            ticket,
            message=f"Major incident declared ({severity})",
            event_type="declared",
            author=actor,
            is_public=True,
        )
        AuditService.log(
            action="incident.major_declared",
            ticket=ticket,
            company=ticket.company,
            actor=actor,
            message=customer_impact or "Major incident declared",
            metadata={"severity": severity},
        )
        if commander:
            NotificationService.create(
                recipient=commander,
                subject=f"[{ticket.ticket_number}] You are incident commander",
                body=customer_impact or ticket.title,
                ticket=ticket,
                send_email=True,
            )
        logger.info("major_incident ticket=%s severity=%s", ticket.ticket_number, severity)
        return record

    @staticmethod
    def add_timeline(
        ticket: Ticket,
        *,
        message: str,
        event_type: str = "update",
        author=None,
        is_public: bool = False,
    ) -> IncidentTimelineEvent:
        return IncidentTimelineEvent.objects.create(
            ticket=ticket,
            author=author,
            event_type=event_type,
            message=message,
            is_public=is_public,
        )

    @classmethod
    @transaction.atomic
    def resolve_major(cls, ticket: Ticket, *, actor=None, postmortem_url: str = "") -> MajorIncident:
        record = getattr(ticket, "major_incident_record", None)
        if record is None:
            raise ValueError("Ticket is not a declared major incident")
        record.resolved_at = timezone.now()
        record.postmortem_url = postmortem_url
        record.save(update_fields=["resolved_at", "postmortem_url", "updated_at"])
        cls.add_timeline(
            ticket,
            message="Major incident resolved",
            event_type="resolved",
            author=actor,
            is_public=True,
        )
        return record

    @staticmethod
    def timeline(ticket: Ticket, public_only: bool = False):
        qs = ticket.incident_timeline.select_related("author").all()
        if public_only:
            qs = qs.filter(is_public=True)
        return qs