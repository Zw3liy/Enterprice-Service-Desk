from django.contrib import admin

from apps.webhooks.models import WebhookDelivery


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "endpoint", "status", "response_code", "attempt", "created_at")
    list_filter = ("status", "event", "company")
    search_fields = ("event", "error_message", "endpoint__name")
    readonly_fields = (
        "company",
        "endpoint",
        "event",
        "payload",
        "status",
        "response_code",
        "response_body",
        "error_message",
        "attempt",
        "delivered_at",
        "created_at",
        "updated_at",
    )