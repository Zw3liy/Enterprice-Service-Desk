from django.contrib import admin

from apps.customer_portal.models import PortalAnnouncement, PortalProfile


@admin.register(PortalProfile)
class PortalProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "company", "department_name", "notify_email")
    list_filter = ("company",)
    search_fields = ("user__username", "display_name")


@admin.register(PortalAnnouncement)
class PortalAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "is_active", "priority", "starts_at", "ends_at")
    list_filter = ("company", "is_active")
    search_fields = ("title", "body")