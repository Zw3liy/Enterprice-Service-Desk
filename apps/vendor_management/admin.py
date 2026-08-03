from django.contrib import admin

from apps.vendor_management.models import Vendor, VendorContract


class VendorContractInline(admin.TabularInline):
    model = VendorContract
    extra = 0


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "support_email", "risk_rating", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("name", "code", "support_email")
    inlines = [VendorContractInline]


@admin.register(VendorContract)
class VendorContractAdmin(admin.ModelAdmin):
    list_display = ("title", "vendor", "status", "start_date", "end_date", "annual_value")
    list_filter = ("status",)
