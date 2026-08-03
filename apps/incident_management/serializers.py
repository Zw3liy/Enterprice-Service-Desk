from rest_framework import serializers

from apps.incident_management.models import IncidentTimelineEvent, MajorIncident
from apps.service_desk.api.serializers import TicketDetailSerializer, TicketListSerializer


class MajorIncidentSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True)

    class Meta:
        model = MajorIncident
        fields = (
            "id",
            "ticket",
            "ticket_number",
            "company",
            "severity",
            "bridge_channel",
            "commander",
            "customer_impact",
            "status_page_url",
            "declared_at",
            "resolved_at",
            "postmortem_required",
            "postmortem_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("declared_at", "created_at", "updated_at")


class IncidentTimelineSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True, default=None)

    class Meta:
        model = IncidentTimelineEvent
        fields = (
            "id",
            "ticket",
            "author",
            "author_name",
            "event_type",
            "message",
            "is_public",
            "created_at",
        )
        read_only_fields = ("author", "created_at")


class DeclareMajorSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(
        choices=MajorIncident.Severity.choices, default=MajorIncident.Severity.SEV1
    )
    commander = serializers.IntegerField(required=False, allow_null=True)
    customer_impact = serializers.CharField(required=False, allow_blank=True, default="")
    bridge_channel = serializers.CharField(required=False, allow_blank=True, default="")


class IncidentTicketSerializer(TicketListSerializer):
    is_major_incident = serializers.BooleanField(read_only=True)