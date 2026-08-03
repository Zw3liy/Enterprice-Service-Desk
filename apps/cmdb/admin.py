from django.contrib import admin

from apps.cmdb.models import CIClass, CIRelationship, ConfigurationItem, DiscoveryResult


@admin.register(CIClass)
class CIClassAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "company", "icon")
    list_filter = ("company",)
    search_fields = ("name", "code")


@admin.register(ConfigurationItem)
class ConfigurationItemAdmin(admin.ModelAdmin):
    list_display = ("ci_id", "name", "ci_class", "environment", "criticality", "is_active")
    list_filter = ("company", "environment", "is_active", "ci_class")
    search_fields = ("ci_id", "name")
    raw_id_fields = ("asset", "company", "ci_class")


@admin.register(CIRelationship)
class CIRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source", "relation_type", "target")
    list_filter = ("relation_type",)


@admin.register(DiscoveryResult)
class DiscoveryResultAdmin(admin.ModelAdmin):
    list_display = ("hostname", "ip_address", "source", "processed", "matched_ci", "created_at")
    list_filter = ("processed", "source", "company")