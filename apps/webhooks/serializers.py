from rest_framework import serializers

from apps.service_desk.models import WebhookEndpoint
from apps.webhooks.models import WebhookDelivery


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = (
            "id",
            "company",
            "name",
            "url",
            "secret",
            "events",
            "is_active",
            "headers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {"secret": {"write_only": True, "required": False}}


class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = (
            "id",
            "company",
            "endpoint",
            "endpoint_name",
            "event",
            "payload",
            "status",
            "response_code",
            "response_body",
            "error_message",
            "attempt",
            "delivered_at",
            "created_at",
        )


class WebhookTestSerializer(serializers.Serializer):
    event = serializers.CharField(default="test.ping")
    payload = serializers.DictField(required=False, default=dict)