from rest_framework import serializers

from apps.problem_management.models import ProblemRecord
from apps.service_desk.api.serializers import TicketListSerializer


class ProblemRecordSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True)
    title = serializers.CharField(source="ticket.title", read_only=True)

    class Meta:
        model = ProblemRecord
        fields = (
            "id",
            "ticket",
            "ticket_number",
            "title",
            "company",
            "state",
            "root_cause",
            "workaround",
            "known_error_article",
            "owner",
            "related_incidents",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class ProblemCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    auto_assign = serializers.BooleanField(default=False)


class RootCauseSerializer(serializers.Serializer):
    root_cause = serializers.CharField()
    workaround = serializers.CharField(required=False, allow_blank=True, default="")


class LinkIncidentSerializer(serializers.Serializer):
    incident_id = serializers.IntegerField()


class ProblemTicketSerializer(TicketListSerializer):
    pass