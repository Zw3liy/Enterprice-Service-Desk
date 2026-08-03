from django.apps import AppConfig


class CMDBConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cmdb"
    label = "cmdb"
    verbose_name = "CMDB"