from django.contrib import admin

from .models import Department, RequestType, Ticket, Supplier


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "created_at",
    )
    search_fields = (
        "name",
    )


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "created_at",
    )
    search_fields = (
        "name",
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "priority",
        "urgency",
        "status",
        "department",
        "request_type",
        "assigned_to",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "urgency",
        "department",
        "request_type",
    )

    search_fields = (
        "title",
        "description",
    )

    autocomplete_fields = (
        "department",
        "request_type",
        "assigned_to",
        "created_by",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "contact_name",
        "contact_email",
        "phone",
        "department",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "department",
    )
    search_fields = (
        "name",
        "contact_name",
        "contact_email",
        "phone",
    )
    autocomplete_fields = (
        "department",
    )
    ordering = (
        "name",
    )