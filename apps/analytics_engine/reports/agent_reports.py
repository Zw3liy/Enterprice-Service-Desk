from django.db.models import Count

from apps.service_desk.models import Ticket


def agent_workload_report(company=None) -> list[dict]:
    qs = Ticket.objects.filter(closed_at__isnull=True)
    if company is not None:
        qs = qs.filter(company=company)
    rows = (
        qs.values("assignee__username")
        .annotate(open_count=Count("id"))
        .order_by("-open_count")
    )
    return [
        {
            "agent": row["assignee__username"] or "Unassigned",
            "open_count": row["open_count"],
        }
        for row in rows
    ]
