from django.apps import AppConfig


class PAMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pam"
    label = "pam"
    verbose_name = "Privileged Access Management"