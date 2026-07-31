"""CSV export helpers for reporting."""

from __future__ import annotations

import csv
from io import StringIO

from apps.service_desk.models import Ticket


def tickets_csv(queryset=None) -> str:
    qs = queryset if queryset is not None else Ticket.objects.all()
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "ticket_number",
            "title",
            "type",
            "status",
            "priority",
            "assignee",
            "created_at",
            "resolved_at",
            "sla_breached",
        ]
    )
    for t in qs.select_related("status", "priority", "assignee").iterator():
        writer.writerow(
            [
                t.ticket_number,
                t.title,
                t.ticket_type,
                t.status.name if t.status_id else "",
                t.priority.name if t.priority_id else "",
                t.assignee.username if t.assignee_id else "",
                t.created_at.isoformat() if t.created_at else "",
                t.resolved_at.isoformat() if t.resolved_at else "",
                t.sla_resolution_breached,
            ]
        )
    return buf.getvalue()
