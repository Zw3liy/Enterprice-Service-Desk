from django.contrib import admin

from apps.inventory.models import StockItem, StockLevel, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("code", "name")


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "unit", "reorder_level", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("sku", "name")


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ("item", "warehouse", "quantity", "updated_at")
    list_filter = ("warehouse",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "warehouse",
        "movement_type",
        "quantity",
        "reference",
        "created_by",
        "created_at",
    )
    list_filter = ("movement_type", "company")
