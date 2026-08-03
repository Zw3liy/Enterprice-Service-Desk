from rest_framework import serializers

from apps.soc_center.models import PlaybookRun, SecurityIncident, SOCPlaybook


class SecurityIncidentSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(
        source="ticket.ticket_number", read_only=True, default=None
    )

    class Meta:
        model = SecurityIncident
        fields = (
            "id",
            "company",
            "ticket",
            "ticket_number",
            "title",
            "summary",
            "severity",
            "state",
            "category",
            "source",
            "assignee",
            "detected_at",
            "contained_at",
            "closed_at",
            "iocs",
            "mitre_tactics",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("detected_at", "contained_at", "closed_at", "created_at", "updated_at")


class SecurityIncidentCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    severity = serializers.ChoiceField(
        choices=SecurityIncident.Severity.choices, default=SecurityIncident.Severity.MEDIUM
    )
    category = serializers.CharField(required=False, default="general")
    source = serializers.CharField(required=False, default="manual")
    iocs = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    mitre_tactics = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    create_ticket = serializers.BooleanField(default=True)


class SOCPlaybookSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOCPlaybook
        fields = (
            "id",
            "company",
            "name",
            "code",
            "description",
            "steps",
            "is_active",
            "created_at",
        )


class PlaybookRunSerializer(serializers.ModelSerializer):
    playbook_name = serializers.CharField(source="playbook.name", read_only=True)

    class Meta:
        model = PlaybookRun
        fields = (
            "id",
            "security_incident",
            "playbook",
            "playbook_name",
            "state",
            "current_step",
            "log",
            "started_by",
            "finished_at",
            "created_at",
        )
