from rest_framework import serializers

from apps.pam.models import AccessRequest, PrivilegedAccount, PrivilegedSession


class PrivilegedAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegedAccount
        fields = (
            "id",
            "company",
            "name",
            "system",
            "username",
            "environment",
            "is_active",
            "metadata",
            "created_at",
        )


class AccessRequestSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = AccessRequest
        fields = (
            "id",
            "company",
            "account",
            "account_name",
            "requester",
            "approver",
            "justification",
            "state",
            "requested_minutes",
            "starts_at",
            "ends_at",
            "decided_at",
            "decision_note",
            "created_at",
        )
        read_only_fields = (
            "requester",
            "approver",
            "state",
            "starts_at",
            "ends_at",
            "decided_at",
            "created_at",
        )


class AccessRequestCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    justification = serializers.CharField()
    requested_minutes = serializers.IntegerField(min_value=5, max_value=1440, default=60)
    approver_id = serializers.IntegerField(required=False, allow_null=True)


class PrivilegedSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegedSession
        fields = (
            "id",
            "access_request",
            "state",
            "started_at",
            "ended_at",
            "session_token",
            "client_ip",
            "audit_trail",
        )
        read_only_fields = fields
