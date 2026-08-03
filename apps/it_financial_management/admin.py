from django.contrib import admin

from apps.it_financial_management.models import Budget, ChargebackEntry, CostCenter


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "owner", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("code", "name")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("cost_center", "fiscal_year", "amount", "currency", "company")
    list_filter = ("fiscal_year", "company")


@admin.register(ChargebackEntry)
class ChargebackEntryAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "cost_center",
        "category",
        "amount",
        "currency",
        "posted_on",
        "ticket",
    )
    list_filter = ("category", "company")
    search_fields = ("description",)
