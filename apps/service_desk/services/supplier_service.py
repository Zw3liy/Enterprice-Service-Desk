from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import Supplier


class SupplierService:
    """
    Supplier Management business service.

    All supplier mutation goes through here so that validation,
    department scoping and lifecycle rules cannot be bypassed by a
    view writing to the model directly.
    """

    # ==========================================================
    # Scoping helpers
    # ==========================================================

    @staticmethod
    def assert_department_allowed(user, department) -> None:
        """
        Reject an attempt to file a supplier under a department the
        acting user does not manage.

        Without this, a Manager could create a supplier against
        another department — a record they would then immediately
        lose sight of, and one that would appear in a peer manager's
        scoped list. Administrators (and superusers) are unrestricted.
        """

        from apps.service_desk.security.policies import is_administrator

        if user is None or is_administrator(user):
            return

        if department is None:
            # An unscoped supplier is only visible to Administrators
            # (see get_supplier_queryset), so a Manager creating one
            # would be writing a record they cannot read back.
            raise ValidationError(
                "Select a department you manage for this supplier."
            )

        if not user.managed_departments.filter(pk=department.pk).exists():
            raise ValidationError(
                "You can only manage suppliers for departments you manage."
            )

    # ==========================================================
    # Create / update
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_supplier(user=None, **data: Any) -> Supplier:
        department = data.get("department")

        SupplierService.assert_department_allowed(user, department)

        # Mirror update_supplier behaviour: validate before saving
        supplier = Supplier(**data)
        supplier.full_clean()
        supplier.save()
        return supplier

    @staticmethod
    @transaction.atomic
    def update_supplier(supplier: Supplier, user=None, **fields: Any) -> Supplier:
        if "department" in fields:
            SupplierService.assert_department_allowed(
                user, fields["department"]
            )

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

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def deactivate_supplier(supplier: Supplier, user=None) -> Supplier:
        """
        Retire a supplier without deleting it.

        Supplier records are referenced by procurement history, so the
        lifecycle is active/inactive rather than a hard delete.
        """

        if not supplier.is_active:
            raise ValidationError("Supplier is already inactive.")

        supplier.is_active = False
        supplier.save(update_fields=["is_active", "updated_at"])
        return supplier

    @staticmethod
    @transaction.atomic
    def activate_supplier(supplier: Supplier, user=None) -> Supplier:
        if supplier.is_active:
            raise ValidationError("Supplier is already active.")

        supplier.is_active = True
        supplier.save(update_fields=["is_active", "updated_at"])
        return supplier
