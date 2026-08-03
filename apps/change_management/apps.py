from django.apps import AppConfig


class ChangeManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.change_management"
    label = "change_management"
    verbose_name = "Change Management"