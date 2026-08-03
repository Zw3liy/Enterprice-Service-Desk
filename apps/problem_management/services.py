"""Problem management services."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.problem_management.models import ProblemRecord
from apps.service_desk.models import Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class ProblemService:
    @classmethod
    @transaction.atomic
    def create_problem(cls, **kwargs) -> Ticket:
        kwargs.setdefault("ticket_type", Ticket.TicketType.PROBLEM)
        ticket = TicketService.create_ticket(**kwargs)
        ProblemRecord.objects.create(
            ticket=ticket,
            company=ticket.company,
            owner=kwargs.get("assignee") or kwargs.get("actor"),
        )
        return ticket

    @staticmethod
    def open_problems(company=None):
        return TicketService.search(
            company=company,
            ticket_type=Ticket.TicketType.PROBLEM,
            open_only=True,
        )

    @classmethod
    @transaction.atomic
    def link_incident(cls, problem_ticket: Ticket, incident: Ticket) -> ProblemRecord:
        record, _ = ProblemRecord.objects.get_or_create(
            ticket=problem_ticket,
            defaults={"company": problem_ticket.company},
        )
        record.related_incidents.add(incident)
        problem_ticket.related_tickets.add(incident)
        if incident.parent_id is None:
            incident.parent = problem_ticket
            incident.save(update_fields=["parent", "updated_at"])
        AuditService.log(
            action="problem.linked_incident",
            ticket=problem_ticket,
            company=problem_ticket.company,
            message=f"Linked incident {incident.ticket_number}",
            metadata={"incident_id": incident.pk},
        )
        return record

    @classmethod
    def set_root_cause(
        cls,
        problem_ticket: Ticket,
        *,
        root_cause: str,
        workaround: str = "",
        actor=None,
    ) -> ProblemRecord:
        record, _ = ProblemRecord.objects.get_or_create(
            ticket=problem_ticket,
            defaults={"company": problem_ticket.company},
        )
        record.root_cause = root_cause
        record.workaround = workaround
        record.state = ProblemRecord.State.ROOT_CAUSE
        if workaround:
            record.state = ProblemRecord.State.KNOWN_ERROR
        record.save()
        AuditService.log(
            action="problem.root_cause",
            ticket=problem_ticket,
            company=problem_ticket.company,
            actor=actor,
            message=root_cause[:500],
        )
        return record

    @classmethod
    def mark_known_error(
        cls, problem_ticket: Ticket, *, article=None, actor=None
    ) -> ProblemRecord:
        record, _ = ProblemRecord.objects.get_or_create(
            ticket=problem_ticket,
            defaults={"company": problem_ticket.company},
        )
        record.state = ProblemRecord.State.KNOWN_ERROR
        if article is not None:
            record.known_error_article = article
        record.save()
        AuditService.log(
            action="problem.known_error",
            ticket=problem_ticket,
            company=problem_ticket.company,
            actor=actor,
            message="Promoted to known error",
        )
        return record