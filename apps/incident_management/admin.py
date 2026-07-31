from django.contrib import admin

from apps.incident_management.models import IncidentTimelineEvent, MajorIncident


@admin.register(MajorIncident)
class MajorIncidentAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "severity",
        "commander",
        "declared_at",
        "resolved_at",
        "company",
    )
    list_filter = ("severity", "company")
    search_fields = ("ticket__ticket_number", "customer_impact")
    raw_id_fields = ("ticket", "commander", "company")


@admin.register(IncidentTimelineEvent)
class IncidentTimelineEventAdmin(admin.ModelAdmin):
    list_display = ("ticket", "event_type", "author", "is_public", "created_at")
    list_filter = ("event_type", "is_public")
    search_fields = ("message", "ticket__ticket_number")