"""Dashboard metrics and executive KPIs."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Optional

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.service_desk.models import (
    Asset,
    CustomerFeedback,
    KnowledgeArticle,
    Ticket,
)


class DashboardService:
    @classmethod
    def summary(cls, *, company=None, user=None) -> dict[str, Any]:
        tickets = Ticket.objects.all()
        if company is not None:
            tickets = tickets.filter(company=company)

        open_q = Q(closed_at__isnull=True) & (
            Q(status__isnull=True) | Q(status__is_terminal=False)
        )
        now = timezone.now()
        last_7 = now - timedelta(days=7)
        last_30 = now - timedelta(days=30)

        total = tickets.count()
        open_count = tickets.filter(open_q).count()
        resolved = tickets.filter(resolved_at__isnull=False).count()
        breached = tickets.filter(
            Q(sla_response_breached=True) | Q(sla_resolution_breached=True)
        ).count()
        unassigned = tickets.filter(open_q, assignee__isnull=True).count()
        major = tickets.filter(open_q, is_major_incident=True).count()
        created_7d = tickets.filter(created_at__gte=last_7).count()
        resolved_7d = tickets.filter(resolved_at__gte=last_7).count()
        created_30d = tickets.filter(created_at__gte=last_30).count()

        by_priority = list(
            tickets.filter(open_q)
            .values("priority__name", "priority__colour")
            .annotate(count=Count("id"))
            .order_by("priority__rank")
        )
        by_status = list(
            tickets.filter(open_q)
            .values("status__name", "status__colour")
            .annotate(count=Count("id"))
            .order_by("status__rank")
        )
        by_type = list(
            tickets.values("ticket_type").annotate(count=Count("id")).order_by("-count")
        )

        trend = list(
            tickets.filter(created_at__gte=last_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        avg_csat = (
            CustomerFeedback.objects.filter(ticket__in=tickets).aggregate(
                avg=Avg("rating")
            )["avg"]
        )

        my_open = 0
        if user is not None and user.is_authenticated:
            my_open = tickets.filter(open_q, assignee=user).count()

        assets_total = Asset.objects.all()
        articles = KnowledgeArticle.objects.filter(is_published=True)
        if company is not None:
            assets_total = assets_total.filter(company=company)
            articles = articles.filter(company=company)

        return {
            "total_tickets": total,
            "open_tickets": open_count,
            "resolved_tickets": resolved,
            "breached_tickets": breached,
            "unassigned_tickets": unassigned,
            "major_incidents": major,
            "created_7d": created_7d,
            "resolved_7d": resolved_7d,
            "created_30d": created_30d,
            "by_priority": by_priority,
            "by_status": by_status,
            "by_type": by_type,
            "trend": [
                {"day": row["day"].isoformat() if row["day"] else "", "count": row["count"]}
                for row in trend
            ],
            "trend_json": json.dumps(
                [
                    {
                        "day": row["day"].isoformat() if row["day"] else "",
                        "count": row["count"],
                    }
                    for row in trend
                ]
            ),
            "avg_csat": round(float(avg_csat), 2) if avg_csat is not None else None,
            "my_open_tickets": my_open,
            "assets_total": assets_total.count(),
            "knowledge_articles": articles.count(),
            "sla_compliance_pct": cls._sla_compliance(tickets),
        }

    @staticmethod
    def _sla_compliance(tickets) -> Optional[float]:
        resolved = tickets.filter(resolved_at__isnull=False, sla__isnull=False)
        total = resolved.count()
        if total == 0:
            return None
        ok = resolved.filter(sla_resolution_breached=False).count()
        return round((ok / total) * 100, 1)

    @classmethod
    def recent_tickets(cls, *, company=None, limit: int = 10):
        qs = Ticket.objects.select_related("status", "priority", "assignee").order_by(
            "-created_at"
        )
        if company is not None:
            qs = qs.filter(company=company)
        return list(qs[:limit])
