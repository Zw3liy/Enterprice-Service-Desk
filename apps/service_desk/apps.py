from django.apps import AppConfig


class ServiceDeskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service_desk"
    label = "service_desk"
    verbose_name = "Enterprise Service Desk"

    def ready(self) -> None:
        # Register signal handlers
        from apps.service_desk import signals  # noqa: F401
        from apps.service_desk import signals_webhooks  # noqa: F401
