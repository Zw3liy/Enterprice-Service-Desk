"""Inventory application services."""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import F, Sum
from django.utils.text import slugify

from apps.inventory.models import StockItem, StockLevel, StockMovement, Warehouse

logger = logging.getLogger(__name__)


class InventoryService:
    @staticmethod
    def ensure_warehouse(company, code: str = "main", name: str = "Main warehouse") -> Warehouse:
        wh, _ = Warehouse.objects.get_or_create(
            company=company,
            code=slugify(code)[:40],
            defaults={"name": name, "is_active": True},
        )
        return wh

    @staticmethod
    def upsert_item(company, *, sku: str, name: str, **kwargs) -> StockItem:
        item, _ = StockItem.objects.update_or_create(
            company=company,
            sku=sku,
            defaults={"name": name, **kwargs, "is_active": True},
        )
        return item

    @classmethod
    @transaction.atomic
    def move(
        cls,
        *,
        company,
        warehouse: Warehouse,
        item: StockItem,
        movement_type: str,
        quantity: int,
        reference: str = "",
        notes: str = "",
        user=None,
    ) -> StockMovement:
        if quantity == 0:
            raise ValueError("quantity cannot be zero")
        signed = quantity
        if movement_type == StockMovement.MovementType.ISSUE and quantity > 0:
            signed = -quantity
        if movement_type == StockMovement.MovementType.RECEIPT and quantity < 0:
            signed = abs(quantity)

        level, _ = StockLevel.objects.select_for_update().get_or_create(
            warehouse=warehouse, item=item, defaults={"quantity": 0}
        )
        new_qty = level.quantity + signed
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        level.quantity = new_qty
        level.save(update_fields=["quantity", "updated_at"])

        movement = StockMovement.objects.create(
            company=company,
            warehouse=warehouse,
            item=item,
            movement_type=movement_type,
            quantity=signed,
            reference=reference,
            notes=notes,
            created_by=user,
        )
        logger.info(
            "stock_move item=%s wh=%s qty=%s type=%s",
            item.sku,
            warehouse.code,
            signed,
            movement_type,
        )
        return movement

    @staticmethod
    def on_hand(item: StockItem) -> int:
        total = item.levels.aggregate(t=Sum("quantity"))["t"]
        return int(total or 0)

    @staticmethod
    def below_reorder(company):
        items = []
        for item in StockItem.objects.filter(company=company, is_active=True):
            qty = InventoryService.on_hand(item)
            if qty <= item.reorder_level:
                items.append({"item": item, "on_hand": qty, "reorder_level": item.reorder_level})
        return items
