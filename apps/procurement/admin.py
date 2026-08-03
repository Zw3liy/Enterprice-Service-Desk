from django.contrib import admin

from apps.procurement.models import PurchaseOrder, PurchaseRequest, PurchaseRequestLine


class PurchaseRequestLineInline(admin.TabularInline):
    model = PurchaseRequestLine
    extra = 0


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "title",
        "state",
        "requester",
        "total_estimate",
        "currency",
        "company",
    )
    list_filter = ("state", "company")
    search_fields = ("number", "title")
    inlines = [PurchaseRequestLineInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "vendor",
        "state",
        "total",
        "currency",
        "ordered_at",
        "company",
    )
    list_filter = ("state", "company")
    search_fields = ("number", "notes")
    raw_id_fields = ("purchase_request", "vendor", "company", "created_by")
