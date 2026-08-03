from rest_framework import serializers

from apps.inventory.models import StockItem, StockLevel, StockMovement, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "company", "code", "name", "location", "is_active", "created_at")


class StockItemSerializer(serializers.ModelSerializer):
    on_hand = serializers.SerializerMethodField()

    class Meta:
        model = StockItem
        fields = (
            "id",
            "company",
            "sku",
            "name",
            "description",
            "unit",
            "reorder_level",
            "is_active",
            "on_hand",
            "created_at",
        )

    def get_on_hand(self, obj):
        from apps.inventory.services import InventoryService

        return InventoryService.on_hand(obj)


class StockLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLevel
        fields = ("id", "warehouse", "item", "quantity", "updated_at")


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = (
            "id",
            "company",
            "warehouse",
            "item",
            "movement_type",
            "quantity",
            "reference",
            "notes",
            "created_by",
            "created_at",
        )
        read_only_fields = ("created_by", "created_at")


class StockMoveSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    item_id = serializers.IntegerField()
    movement_type = serializers.ChoiceField(choices=StockMovement.MovementType.choices)
    quantity = serializers.IntegerField()
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
