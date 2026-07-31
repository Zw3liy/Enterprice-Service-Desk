from django.apps import AppConfig


class ScheduledReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scheduled_reports"
    label = "scheduled_reports"
    verbose_name = "Scheduled Reports"