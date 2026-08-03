from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class AnalyticsSnapshot(TimeStampedModel):
    """Point-in-time KPI snapshot for historical analytics."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="analytics_snapshots"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    metrics = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=40, default="dashboard")

    class Meta:
        ordering = ["-period_end", "-created_at"]
        indexes = [
            models.Index(fields=["company", "period_end"]),
        ]

    def __str__(self) -> str:
        return f"{self.company_id} {self.period_start}→{self.period_end}"
