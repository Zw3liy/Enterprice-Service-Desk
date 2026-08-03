from django.contrib import admin

from apps.pam.models import AccessRequest, PrivilegedAccount, PrivilegedSession


@admin.register(PrivilegedAccount)
class PrivilegedAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "system", "username", "environment", "is_active", "company")
    list_filter = ("environment", "is_active", "company")
    search_fields = ("name", "system", "username")


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "requester",
        "state",
        "requested_minutes",
        "starts_at",
        "ends_at",
        "company",
    )
    list_filter = ("state", "company")
    search_fields = ("justification", "account__name", "requester__username")


@admin.register(PrivilegedSession)
class PrivilegedSessionAdmin(admin.ModelAdmin):
    list_display = ("access_request", "state", "started_at", "ended_at", "client_ip")
    list_filter = ("state",)
    readonly_fields = ("session_token", "audit_trail")
