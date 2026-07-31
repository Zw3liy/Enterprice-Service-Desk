from django.apps import AppConfig


class IncidentManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.incident_management"
    label = "incident_management"
    verbose_name = "Incident Management"