from django.contrib import admin

from apps.business_rules.models import BusinessRule


@admin.register(BusinessRule)
class BusinessRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "scope", "priority", "is_active", "company")
    list_filter = ("scope", "is_active", "company")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}
