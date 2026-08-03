from rest_framework import serializers

from apps.cmdb.models import CIClass, CIRelationship, ConfigurationItem, DiscoveryResult
from apps.service_desk.api.serializers import AssetSerializer


class CIClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = CIClass
        fields = ("id", "company", "name", "code", "description", "icon")


class ConfigurationItemSerializer(serializers.ModelSerializer):
    ci_class_name = serializers.CharField(source="ci_class.name", read_only=True, default=None)
    asset_detail = AssetSerializer(source="asset", read_only=True)

    class Meta:
        model = ConfigurationItem
        fields = (
            "id",
            "uuid",
            "company",
            "asset",
            "asset_detail",
            "ci_class",
            "ci_class_name",
            "name",
            "ci_id",
            "environment",
            "criticality",
            "attributes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("uuid", "created_at", "updated_at")


class CIRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = CIRelationship
        fields = ("id", "source", "target", "relation_type", "notes", "created_at")


class DiscoveryIngestSerializer(serializers.Serializer):
    hostname = serializers.CharField(required=False, allow_blank=True, default="")
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    mac_address = serializers.CharField(required=False, allow_blank=True, default="")
    os_name = serializers.CharField(required=False, allow_blank=True, default="")
    extra = serializers.DictField(required=False, default=dict)


class DiscoveryResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoveryResult
        fields = (
            "id",
            "company",
            "source",
            "hostname",
            "ip_address",
            "mac_address",
            "os_name",
            "matched_ci",
            "processed",
            "raw",
            "created_at",
        )