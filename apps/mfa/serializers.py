from rest_framework import serializers

from apps.mfa.models import MFADevice


class MFADeviceSerializer(serializers.ModelSerializer):
    provisioning_uri = serializers.SerializerMethodField()

    class Meta:
        model = MFADevice
        fields = (
            "id",
            "name",
            "is_active",
            "confirmed_at",
            "last_used_at",
            "provisioning_uri",
            "created_at",
        )
        read_only_fields = fields

    def get_provisioning_uri(self, obj):
        if obj.is_active:
            return ""
        return obj.provisioning_uri()


class MFAEnrollSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, default="Authenticator")


class MFAConfirmSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    token = serializers.CharField(max_length=12)


class MFAVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=16)