from django.contrib import admin

from apps.mfa.models import MFABackupCode, MFADevice


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "is_active", "confirmed_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "name")
    readonly_fields = ("secret",)


@admin.register(MFABackupCode)
class MFABackupCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "used_at", "created_at")
    list_filter = ("used_at",)