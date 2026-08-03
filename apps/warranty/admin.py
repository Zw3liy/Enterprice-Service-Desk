from django.contrib import admin

from apps.warranty.models import WarrantyRecord


@admin.register(WarrantyRecord)
class WarrantyRecordAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "provider_name",
        "contract_number",
        "status",
        "start_date",
        "end_date",
        "company",
    )
    list_filter = ("status", "company")
    search_fields = ("contract_number", "provider_name", "asset__asset_tag")
    raw_id_fields = ("asset", "vendor", "company")
