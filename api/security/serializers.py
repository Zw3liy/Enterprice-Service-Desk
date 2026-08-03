from rest_framework import serializers


class SecurityStatusSerializer(serializers.Serializer):
    mfa_enabled = serializers.BooleanField()
    sso_providers = serializers.ListField(child=serializers.CharField())
