from django.contrib import admin

from .models import (
    CatalogItem,
    Department,
    RequestType,
    Notification,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestApproval,
    SLAEscalation,
    SLAPolicy,
    Supplier,
    Ticket,
    TicketSLA,
)


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

@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "priority",
        "department",
        "response_minutes",
        "resolution_minutes",
        "warning_threshold_percent",
        "is_active",
    )

    list_filter = (
        "priority",
        "department",
        "is_active",
    )

    search_fields = (
        "name",
    )


@admin.register(TicketSLA)
class TicketSLAAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "policy",
        "response_due_at",
        "resolution_due_at",
        "first_responded_at",
        "resolved_at",
        "response_breached",
        "resolution_breached",
        "paused",
    )

    list_filter = (
        "response_breached",
        "resolution_breached",
        "paused",
    )

    raw_id_fields = (
        "ticket",
    )


@admin.register(SLAEscalation)
class SLAEscalationAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_sla",
        "kind",
        "created_at",
    )

    list_filter = (
        "kind",
    )

    raw_id_fields = (
        "ticket_sla",
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "kind",
        "subject",
        "emailed",
        "read_at",
        "created_at",
    )

    list_filter = (
        "kind",
        "emailed",
    )

    search_fields = (
        "subject",
        "body",
    )

    raw_id_fields = (
        "recipient",
        "ticket",
        "problem",
    )


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
    )
    search_fields = (
        "name",
    )


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "fulfillment_department",
        "requires_approval",
        "default_priority",
        "expected_delivery_days",
        "is_active",
    )
    list_filter = (
        "category",
        "fulfillment_department",
        "requires_approval",
        "is_active",
    )
    search_fields = (
        "name",
        "description",
    )
    autocomplete_fields = (
        "category",
        "fulfillment_department",
    )


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "catalog_item",
        "ticket",
        "quantity",
        "status",
        "expected_fulfillment_date",
        "created_at",
    )
    list_filter = (
        "status",
        "catalog_item",
    )
    raw_id_fields = (
        "ticket",
    )
    autocomplete_fields = (
        "catalog_item",
    )


@admin.register(ServiceRequestApproval)
class ServiceRequestApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "service_request",
        "actor",
        "decision",
        "decided_at",
    )
    list_filter = (
        "decision",
    )
    raw_id_fields = (
        "service_request",
        "actor",
    )
