from django.apps import AppConfig


class EventEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.event_engine"
    label = "event_engine"
    verbose_name = "Event Engine"