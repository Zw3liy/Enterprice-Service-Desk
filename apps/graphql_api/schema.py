"""Minimal GraphQL query executor over ESD domain services."""

from __future__ import annotations

from typing import Any

from apps.service_desk.models import Ticket
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.services.ticket_service import TicketService


def execute_query(query: str, variables: dict | None = None, *, user=None, company=None) -> dict[str, Any]:
    """
    Supports a small fixed schema for clients that speak GraphQL-style POSTs:

      query { tickets { id ticketNumber title } }
      query { ticket(id: 1) { id title } }
      query { dashboard { openTickets totalTickets } }
    """
    variables = variables or {}
    q = " ".join((query or "").split())
    data: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    try:
        if "dashboard" in q:
            summary = DashboardService.summary(company=company, user=user)
            data["dashboard"] = {
                "openTickets": summary.get("open_tickets"),
                "totalTickets": summary.get("total_tickets"),
                "resolvedTickets": summary.get("resolved_tickets"),
                "breachedTickets": summary.get("breached_tickets"),
                "slaCompliancePct": summary.get("sla_compliance_pct"),
            }
        if "tickets" in q and "ticket(" not in q.replace(" ", ""):
            qs = TicketService.search(company=company)[:50]
            data["tickets"] = [
                {
                    "id": t.pk,
                    "ticketNumber": t.ticket_number,
                    "title": t.title,
                    "status": t.status.name if t.status_id else None,
                    "priority": t.priority.name if t.priority_id else None,
                }
                for t in qs
            ]
        if "ticket(" in q.replace(" ", "") or variables.get("id") or variables.get("ticketId"):
            ticket_id = variables.get("id") or variables.get("ticketId")
            if ticket_id is None:
                # try parse ticket(id: 123)
                import re

                m = re.search(r"ticket\s*\(\s*id\s*:\s*(\d+)\s*\)", q, re.I)
                if m:
                    ticket_id = int(m.group(1))
            if ticket_id is not None:
                ticket = TicketService.get_ticket(int(ticket_id))
                data["ticket"] = {
                    "id": ticket.pk,
                    "ticketNumber": ticket.ticket_number,
                    "title": ticket.title,
                    "description": ticket.description,
                    "status": ticket.status.name if ticket.status_id else None,
                    "priority": ticket.priority.name if ticket.priority_id else None,
                    "assignee": ticket.assignee.username if ticket.assignee_id else None,
                }
        if not data:
            errors.append({"message": "Unsupported or empty GraphQL selection set"})
    except Ticket.DoesNotExist:
        errors.append({"message": "Ticket not found"})
    except Exception as exc:  # noqa: BLE001
        errors.append({"message": str(exc)})

    payload: dict[str, Any] = {"data": data or None}
    if errors:
        payload["errors"] = errors
    return payload
