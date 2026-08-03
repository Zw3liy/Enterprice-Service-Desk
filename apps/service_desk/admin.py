from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "subject",
        "status",
        "priority",
        "category",
        "created_by",
        "assigned_to",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
        "created_at",
    )

    search_fields = (
        "ticket_number",
        "subject",
        "description",
        "created_by__username",
    )

    readonly_fields = (
        "ticket_number",
        "created_at",
        "updated_at",
        "resolved_at",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (
        (
            "Ticket Information",
            {
                "fields": (
                    "ticket_number",
                    "subject",
                    "description",
                    "category",
                    "priority",
                    "status",
                )
            },
        ),
        (
            "Assignment",
            {
                "fields": (
                    "created_by",
                    "assigned_to",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "resolved_at",
                )
            },
        ),
    )