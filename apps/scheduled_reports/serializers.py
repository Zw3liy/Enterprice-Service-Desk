from rest_framework import serializers

from apps.scheduled_reports.models import ReportRun, ScheduledReport


class ScheduledReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReport
        fields = (
            "id",
            "company",
            "name",
            "report_type",
            "frequency",
            "recipients",
            "is_active",
            "parameters",
            "last_run_at",
            "next_run_at",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("last_run_at", "created_by", "created_at", "updated_at")


class ReportRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportRun
        fields = (
            "id",
            "report",
            "state",
            "row_count",
            "artifact_path",
            "error_message",
            "started_at",
            "finished_at",
        )
