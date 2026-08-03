from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.analytics_engine.models import AnalyticsSnapshot
from apps.service_desk.services.dashboard_service import DashboardService


class MetricsEngine:
    @staticmethod
    def capture_snapshot(company, source: str = "dashboard") -> AnalyticsSnapshot:
        end = timezone.localdate()
        start = end - timedelta(days=30)
        metrics = DashboardService.summary(company=company)
        return AnalyticsSnapshot.objects.create(
            company=company,
            period_start=start,
            period_end=end,
            metrics=metrics,
            source=source,
        )

    @staticmethod
    def latest(company, limit: int = 12):
        return AnalyticsSnapshot.objects.filter(company=company).order_by("-period_end")[
            :limit
        ]
