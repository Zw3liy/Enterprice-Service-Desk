"""Simple time-series forecasting for ticket volume (moving average + trend)."""

from __future__ import annotations

from datetime import timedelta
from statistics import mean

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.service_desk.models import Ticket


class ForecastingService:
    @classmethod
    def ticket_volume_forecast(cls, company, *, history_days: int = 28, horizon_days: int = 7) -> dict:
        end = timezone.localdate()
        start = end - timedelta(days=history_days - 1)
        rows = (
            Ticket.objects.filter(company=company, created_at__date__gte=start, created_at__date__lte=end)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        series = {row["day"]: row["count"] for row in rows}
        history = []
        cursor = start
        while cursor <= end:
            history.append({"day": cursor.isoformat(), "count": int(series.get(cursor, 0))})
            cursor += timedelta(days=1)

        values = [h["count"] for h in history]
        if not values:
            values = [0]
        window = min(7, len(values))
        baseline = mean(values[-window:])
        # linear trend via simple slope between first/last halves
        mid = max(1, len(values) // 2)
        first_avg = mean(values[:mid]) if values[:mid] else baseline
        second_avg = mean(values[mid:]) if values[mid:] else baseline
        daily_slope = (second_avg - first_avg) / max(mid, 1)

        forecast = []
        for i in range(1, horizon_days + 1):
            day = end + timedelta(days=i)
            pred = max(0.0, baseline + daily_slope * i)
            forecast.append(
                {
                    "day": day.isoformat(),
                    "predicted": round(pred, 2),
                    "low": round(max(0.0, pred * 0.7), 2),
                    "high": round(pred * 1.3, 2),
                }
            )
        return {
            "history_days": history_days,
            "horizon_days": horizon_days,
            "baseline": round(baseline, 2),
            "daily_slope": round(daily_slope, 4),
            "history": history,
            "forecast": forecast,
        }

    @classmethod
    def staffing_suggestion(cls, company, tickets_per_agent_per_day: float = 8.0) -> dict:
        forecast = cls.ticket_volume_forecast(company, history_days=14, horizon_days=7)
        avg_pred = mean([p["predicted"] for p in forecast["forecast"]]) if forecast["forecast"] else 0
        agents_needed = int((avg_pred / max(tickets_per_agent_per_day, 0.1)) + 0.999)
        return {
            "avg_predicted_daily_tickets": round(avg_pred, 2),
            "tickets_per_agent_per_day": tickets_per_agent_per_day,
            "suggested_agents": max(1, agents_needed),
            "forecast": forecast["forecast"],
        }
