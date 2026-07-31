from django.contrib import admin

from apps.soc_center.models import PlaybookRun, SecurityIncident, SOCPlaybook


@admin.register(SecurityIncident)
class SecurityIncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "state", "category", "assignee", "detected_at", "company")
    list_filter = ("severity", "state", "category", "company")
    search_fields = ("title", "summary")
    raw_id_fields = ("ticket", "assignee", "company")


@admin.register(SOCPlaybook)
class SOCPlaybookAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("name", "code")


@admin.register(PlaybookRun)
class PlaybookRunAdmin(admin.ModelAdmin):
    list_display = ("playbook", "security_incident", "state", "current_step", "started_by", "created_at")
    list_filter = ("state",)
