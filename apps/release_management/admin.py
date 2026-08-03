from django.contrib import admin

from apps.release_management.models import Release, ReleaseTask


class ReleaseTaskInline(admin.TabularInline):
    model = ReleaseTask
    extra = 0


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "state", "manager", "planned_start", "company")
    list_filter = ("state", "company")
    search_fields = ("name", "version")
    filter_horizontal = ("changes",)
    inlines = [ReleaseTaskInline]


@admin.register(ReleaseTask)
class ReleaseTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "release", "state", "assignee", "sequence")
    list_filter = ("state",)
