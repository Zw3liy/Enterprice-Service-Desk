from django.apps import AppConfig


class MonitoringEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.monitoring_engine"
    label = "monitoring_engine"
    verbose_name = "Monitoring Engine"