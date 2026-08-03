from django.contrib import admin

from apps.multi_tenant.models import TenantDomain, TenantSettings


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "company", "is_primary", "is_verified", "is_active")
    list_filter = ("is_primary", "is_verified", "is_active")
    search_fields = ("domain", "company__name")


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ("company", "data_residency", "max_users", "allow_public_signup")
    search_fields = ("company__name", "company__slug")
