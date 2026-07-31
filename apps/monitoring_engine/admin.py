from django.contrib import admin

from apps.monitoring_engine.models import MonitoringAlert


@admin.register(MonitoringAlert)
class MonitoringAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "severity",
        "state",
        "source",
        "host",
        "ticket",
        "fired_at",
        "company",
    )
    list_filter = ("severity", "state", "source", "company")
    search_fields = ("title", "external_id", "host", "service")
    raw_id_fields = ("ticket", "company")
