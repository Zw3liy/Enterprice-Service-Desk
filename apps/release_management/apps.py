from django.apps import AppConfig


class ReleaseManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.release_management"
    label = "release_management"
    verbose_name = "Release Management"