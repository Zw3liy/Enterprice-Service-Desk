from django.contrib import admin

from .models import (
    Department,
    RequestType,
    CustomField,
    Ticket,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "ticket_counter")


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "department")


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "request_type",
        "field_type",
        "is_required",
    )

    list_filter = (
        "request_type",
        "field_type",
        "is_required",
    )

    search_fields = (
        "name",
    )

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "title",
        "department",
        "request_type",
        "created_at",
    )