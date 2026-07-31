"""Usage metering helpers."""

from __future__ import annotations

from datetime import date

from django.db.models import Count, Sum
from django.utils import timezone

from apps.billing.models import UsageRecord
from apps.service_desk.models import Asset, Ticket


def current_period() -> tuple[date, date]:
    today = timezone.localdate()
    start = today.replace(day=1)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        end = today.replace(month=today.month + 1, day=1)
    from datetime import timedelta

    end = end - timedelta(days=1)
    return start, end


def snapshot_usage(company) -> dict[str, int]:
    start, end = current_period()
    tickets = Ticket.objects.filter(
        company=company, created_at__date__gte=start, created_at__date__lte=end
    ).count()
    assets = Asset.objects.filter(company=company, is_active=True).count()
    agents = company.agents.filter(is_available=True).count() if hasattr(company, "agents") else 0
    metrics = {
        UsageRecord.Metric.TICKETS: tickets,
        UsageRecord.Metric.ASSETS: assets,
        UsageRecord.Metric.AGENTS: agents,
    }
    for metric, qty in metrics.items():
        UsageRecord.objects.update_or_create(
            company=company,
            metric=metric,
            period_start=start,
            period_end=end,
            defaults={"quantity": qty},
        )
    return metrics