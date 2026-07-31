from django.contrib import admin

from apps.integrations.models import IntegrationConnection


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "state", "company", "last_synced_at")
    list_filter = ("provider", "state", "company")
    search_fields = ("name",)
    readonly_fields = ("last_error", "last_synced_at")
