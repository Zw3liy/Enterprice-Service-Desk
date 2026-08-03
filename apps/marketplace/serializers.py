from rest_framework import serializers

from apps.marketplace.models import InstalledApp, MarketplaceApp


class MarketplaceAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceApp
        fields = (
            "id",
            "slug",
            "name",
            "vendor",
            "category",
            "short_description",
            "description",
            "icon",
            "version",
            "config_schema",
            "webhook_events",
            "is_published",
            "is_premium",
            "documentation_url",
        )


class InstalledAppSerializer(serializers.ModelSerializer):
    app_detail = MarketplaceAppSerializer(source="app", read_only=True)

    class Meta:
        model = InstalledApp
        fields = (
            "id",
            "company",
            "app",
            "app_detail",
            "state",
            "config",
            "installed_by",
            "last_sync_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("installed_by", "last_sync_at", "created_at", "updated_at")


class InstallAppSerializer(serializers.Serializer):
    app_slug = serializers.SlugField()
    config = serializers.DictField(required=False, default=dict)
