from rest_framework import serializers

from apps.compliance.models import ComplianceEvidence, Control, ControlFramework


class ControlFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlFramework
        fields = ("id", "company", "name", "code", "description", "version", "created_at")


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = (
            "id",
            "framework",
            "control_id",
            "title",
            "description",
            "status",
            "owner",
            "last_reviewed_at",
            "created_at",
            "updated_at",
        )


class ComplianceEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceEvidence
        fields = (
            "id",
            "control",
            "title",
            "description",
            "url",
            "collected_by",
            "collected_at",
            "created_at",
        )
        read_only_fields = ("collected_by", "collected_at", "created_at")
