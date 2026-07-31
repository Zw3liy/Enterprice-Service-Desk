from rest_framework import serializers

from apps.vendor_management.models import Vendor, VendorContract


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = (
            "id",
            "company",
            "name",
            "code",
            "website",
            "support_email",
            "support_phone",
            "account_manager",
            "notes",
            "is_active",
            "risk_rating",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class VendorContractSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = VendorContract
        fields = (
            "id",
            "vendor",
            "vendor_name",
            "title",
            "contract_number",
            "status",
            "start_date",
            "end_date",
            "annual_value",
            "currency",
            "sla_summary",
            "auto_renew",
            "document_url",
            "created_at",
            "updated_at",
        )
