from django.contrib import admin

from apps.scheduled_reports.models import ReportRun, ScheduledReport


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "report_type",
        "frequency",
        "is_active",
        "last_run_at",
        "next_run_at",
        "company",
    )
    list_filter = ("report_type", "frequency", "is_active", "company")
    search_fields = ("name",)


@admin.register(ReportRun)
class ReportRunAdmin(admin.ModelAdmin):
    list_display = ("report", "state", "row_count", "started_at", "finished_at")
    list_filter = ("state",)
