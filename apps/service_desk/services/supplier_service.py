from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.service_desk.models import Supplier


class SupplierService:
    """
    Supplier Management business service.
    """

    @staticmethod
    @transaction.atomic
    def create_supplier(**data: Any) -> Supplier:
        # Mirror update_supplier behaviour: validate before saving
        supplier = Supplier(**data)
        supplier.full_clean()
        supplier.save()
        return supplier

    @staticmethod
    @transaction.atomic
    def update_supplier(supplier: Supplier, **fields: Any) -> Supplier:
        changed = {}

        for field, value in fields.items():
            if not hasattr(supplier, field):
                continue

            current = getattr(supplier, field)
            if current != value:
                changed[field] = (current, value)
                setattr(supplier, field, value)

        if not changed:
            return supplier

        supplier.full_clean()
        supplier.save()
        return supplier
