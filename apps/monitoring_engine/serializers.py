from rest_framework import serializers

from apps.monitoring_engine.models import MonitoringAlert


class MonitoringAlertSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True, default=None)

    class Meta:
        model = MonitoringAlert
        fields = (
            "id",
            "company",
            "source",
            "external_id",
            "title",
            "description",
            "severity",
            "state",
            "host",
            "service",
            "payload",
            "ticket",
            "ticket_number",
            "fired_at",
            "resolved_at",
            "created_at",
        )
        read_only_fields = ("fired_at", "resolved_at", "created_at", "ticket")


class MonitoringIngestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    severity = serializers.ChoiceField(
        choices=MonitoringAlert.Severity.choices, default=MonitoringAlert.Severity.WARNING
    )
    source = serializers.CharField(required=False, default="generic")
    external_id = serializers.CharField(required=False, allow_blank=True, default="")
    host = serializers.CharField(required=False, allow_blank=True, default="")
    service = serializers.CharField(required=False, allow_blank=True, default="")
    payload = serializers.DictField(required=False, default=dict)
    open_incident = serializers.BooleanField(default=True)
