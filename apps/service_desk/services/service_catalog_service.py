from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import CatalogItem


class CatalogService:
    """
    Service catalogue administration.

    ``ServiceCategory`` has no dedicated service — it is reference
    data managed through Django admin, the same precedent already set
    by ``Department``/``RequestType`` in this codebase. Only
    ``CatalogItem`` (the requestable offering, with a lifecycle) needs
    a business service.
    """

    # ==========================================================
    # Scoping helpers
    # ==========================================================

    @staticmethod
    def assert_department_allowed(user, department) -> None:
        """
        Reject an attempt to route a catalogue item to a department
        the acting user does not manage.

        Mirrors ``SupplierService.assert_department_allowed`` exactly
        — a Manager creating a catalogue item is a mass-assignment
        surface (``fulfillment_department`` is a normal form field)
        that must be checked here, not only narrowed in the form.
        Administrators (and superusers) are unrestricted; an
        unscoped item (``department=None``) is allowed for anyone
        with the create/change permission — it simply has no
        department-based fulfilment routing.
        """

        from apps.service_desk.security.policies import is_administrator

        if user is None or is_administrator(user):
            return

        if department is None:
            return

        if not user.managed_departments.filter(pk=department.pk).exists():
            raise ValidationError(
                "You can only route catalogue items to departments "
                "you manage."
            )

    # ==========================================================
    # Create / update
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_item(user=None, **data: Any) -> CatalogItem:
        CatalogService.assert_department_allowed(
            user, data.get("fulfillment_department")
        )

        item = CatalogItem(**data)
        item.full_clean()
        item.save()
        return item

    @staticmethod
    @transaction.atomic
    def update_item(item: CatalogItem, user=None, **fields: Any) -> CatalogItem:
        if "fulfillment_department" in fields:
            CatalogService.assert_department_allowed(
                user, fields["fulfillment_department"]
            )

        changed = {}

        for field, value in fields.items():
            if not hasattr(item, field):
                continue

            current = getattr(item, field)
            if current != value:
                changed[field] = value
                setattr(item, field, value)

        if not changed:
            return item

        item.full_clean()
        item.save()
        return item

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def deactivate_item(item: CatalogItem) -> CatalogItem:
        """
        Retire a catalogue item without deleting it.

        Existing ``ServiceRequest`` rows reference it (``PROTECT``),
        so the lifecycle is active/inactive, never a hard delete.
        """

        if not item.is_active:
            raise ValidationError("Item is already inactive.")

        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return item

    @staticmethod
    @transaction.atomic
    def activate_item(item: CatalogItem) -> CatalogItem:
        if item.is_active:
            raise ValidationError("Item is already active.")

        item.is_active = True
        item.save(update_fields=["is_active", "updated_at"])
        return item
