from django.contrib import admin

from apps.field_service.models import WorkOrder


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "title",
        "ticket",
        "technician",
        "state",
        "scheduled_start",
        "company",
    )
    list_filter = ("state", "company")
    search_fields = ("number", "title", "location", "ticket__ticket_number")
    raw_id_fields = ("ticket", "technician", "company")
