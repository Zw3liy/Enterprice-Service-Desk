from rest_framework import serializers

from apps.multi_tenant.models import TenantDomain, TenantSettings
from apps.service_desk.models import Company


class CompanyTenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "timezone",
            "primary_email",
            "created_at",
        )


class TenantDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDomain
        fields = (
            "id",
            "company",
            "domain",
            "is_primary",
            "is_verified",
            "is_active",
            "created_at",
        )


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = (
            "id",
            "company",
            "feature_flags",
            "branding",
            "data_residency",
            "max_users",
            "allow_public_signup",
            "updated_at",
        )
        read_only_fields = ("company", "updated_at")


class TenantProvisionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(required=False, allow_blank=True)
    admin_email = serializers.EmailField(required=False, allow_blank=True, default="")
    domain = serializers.CharField(required=False, allow_blank=True, default="")
    plan_code = serializers.SlugField(required=False, default="starter")
