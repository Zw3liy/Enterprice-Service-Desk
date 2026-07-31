from rest_framework import serializers

from apps.warranty.models import WarrantyRecord


class WarrantyRecordSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)

    class Meta:
        model = WarrantyRecord
        fields = (
            "id",
            "company",
            "asset",
            "asset_tag",
            "vendor",
            "provider_name",
            "contract_number",
            "status",
            "start_date",
            "end_date",
            "coverage",
            "support_phone",
            "support_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
