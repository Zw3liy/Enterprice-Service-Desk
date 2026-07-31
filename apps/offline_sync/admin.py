from django.contrib import admin

from apps.offline_sync.models import OfflineMutation, SyncCursor


@admin.register(SyncCursor)
class SyncCursorAdmin(admin.ModelAdmin):
    list_display = ("user", "device_id", "last_pulled_at", "last_pushed_at", "company")
    list_filter = ("company",)
    search_fields = ("device_id", "user__username")


@admin.register(OfflineMutation)
class OfflineMutationAdmin(admin.ModelAdmin):
    list_display = (
        "client_mutation_id",
        "entity_type",
        "operation",
        "state",
        "user",
        "device_id",
        "created_at",
    )
    list_filter = ("state", "entity_type", "operation")
    search_fields = ("client_mutation_id", "entity_id")
