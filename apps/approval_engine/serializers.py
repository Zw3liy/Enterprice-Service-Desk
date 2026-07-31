from rest_framework import serializers

from apps.approval_engine.models import ApprovalPolicy
from apps.service_desk.models import ApprovalRequest


class ApprovalPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalPolicy
        fields = (
            "id",
            "company",
            "name",
            "code",
            "entity_type",
            "conditions",
            "min_approvers",
            "approver_role",
            "is_active",
            "created_at",
        )


class ApprovalRequestSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(
        source="ticket.ticket_number", read_only=True, default=None
    )

    class Meta:
        model = ApprovalRequest
        fields = (
            "id",
            "ticket",
            "ticket_number",
            "requested_by",
            "approver",
            "state",
            "reason",
            "decision_note",
            "decided_at",
            "created_at",
        )
