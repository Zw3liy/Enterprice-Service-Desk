from django.apps import AppConfig


class MultiTenantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.multi_tenant"
    label = "multi_tenant"
    verbose_name = "Multi Tenancy"
