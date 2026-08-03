from rest_framework import serializers

from apps.service_desk.models import Company


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "name", "slug", "is_active", "timezone", "primary_email", "created_at")


class TenantProvisionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(required=False, allow_blank=True)
    admin_email = serializers.EmailField(required=False, allow_blank=True, default="")
