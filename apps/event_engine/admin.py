from django.contrib import admin

from apps.event_engine.models import DomainEvent


@admin.register(DomainEvent)
class DomainEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "correlation_id",
        "company",
        "created_at",
    )
    list_filter = ("event_type", "company")
    search_fields = ("event_type", "aggregate_id", "correlation_id")
    readonly_fields = (
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "payload",
        "metadata",
        "correlation_id",
        "company",
        "created_at",
        "updated_at",
    )
