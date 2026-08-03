from django.contrib import admin

from apps.analytics_engine.models import AnalyticsSnapshot


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("company", "period_start", "period_end", "source", "created_at")
    list_filter = ("source", "company")
    readonly_fields = ("metrics",)
