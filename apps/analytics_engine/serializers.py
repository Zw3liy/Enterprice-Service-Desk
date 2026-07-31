from rest_framework import serializers

from apps.analytics_engine.models import AnalyticsSnapshot


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = (
            "id",
            "company",
            "period_start",
            "period_end",
            "metrics",
            "source",
            "created_at",
        )
