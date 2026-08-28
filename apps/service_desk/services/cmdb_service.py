from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.service_desk.models import CIRelationship, ConfigurationItem


class CMDBService:
    """
    CMDB business service.

    All CI mutation and relationship management goes through here so
    validation (no self-relationships, no duplicate relationships,
    only validated relationship types) and department scoping cannot
    be bypassed by a view writing to the model directly.
    """

    # ==========================================================
    # Scoping helpers
    # ==========================================================

    @staticmethod
    def assert_department_allowed(user, department) -> None:
        """
        Mirrors SupplierService/CatalogService's identically-named
        method — a Manager may only file a CI under a department
        they manage.
        """

        from apps.service_desk.security.policies import is_administrator

        if user is None or is_administrator(user):
            return

        if department is None:
            return

        if not user.managed_departments.filter(pk=department.pk).exists():
            raise ValidationError(
                "You can only manage configuration items for "
                "departments you manage."
            )

    # ==========================================================
    # Create / update
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_ci(user=None, **data: Any) -> ConfigurationItem:
        CMDBService.assert_department_allowed(user, data.get("department"))

        ci = ConfigurationItem(**data)
        ci.full_clean()
        ci.save()
        return ci

    @staticmethod
    @transaction.atomic
    def update_ci(ci: ConfigurationItem, user=None, **fields: Any) -> ConfigurationItem:
        if "department" in fields:
            CMDBService.assert_department_allowed(user, fields["department"])

        changed = {}

        for field, value in fields.items():
            if not hasattr(ci, field):
                continue

            current = getattr(ci, field)
            if current != value:
                changed[field] = value
                setattr(ci, field, value)

        if not changed:
            return ci

        ci.full_clean()
        ci.save()
        return ci

    @staticmethod
    @transaction.atomic
    def change_status(ci: ConfigurationItem, status: str, user=None) -> ConfigurationItem:
        if status not in dict(ConfigurationItem.STATUS_CHOICES):
            raise ValidationError("Invalid status.")

        if ci.status == status:
            return ci

        ci.status = status
        ci.save(update_fields=["status", "updated_at"])
        return ci

    # ==========================================================
    # Relationships
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_relationship(
        source: ConfigurationItem,
        target: ConfigurationItem,
        relationship_type: str,
        user=None,
    ) -> CIRelationship:

        if source.pk == target.pk:
            raise ValidationError(
                "A configuration item cannot have a relationship with itself."
            )

        if relationship_type not in dict(CIRelationship.TYPE_CHOICES):
            raise ValidationError("Invalid relationship type.")

        if CIRelationship.objects.filter(
            source=source, target=target, relationship_type=relationship_type
        ).exists():
            raise ValidationError(
                "This relationship already exists."
            )

        try:
            relationship = CIRelationship.objects.create(
                source=source,
                target=target,
                relationship_type=relationship_type,
                created_by=user,
            )
        except IntegrityError as exc:
            raise ValidationError(
                "This relationship could not be created."
            ) from exc

        return relationship

    @staticmethod
    @transaction.atomic
    def remove_relationship(relationship: CIRelationship) -> None:
        relationship.delete()

    # ==========================================================
    # Ticket / Change linking
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def link_ticket(ci: ConfigurationItem, ticket) -> ConfigurationItem:
        ci.tickets.add(ticket)
        return ci

    @staticmethod
    @transaction.atomic
    def unlink_ticket(ci: ConfigurationItem, ticket) -> ConfigurationItem:
        ci.tickets.remove(ticket)
        return ci

    @staticmethod
    @transaction.atomic
    def link_change(ci: ConfigurationItem, change) -> ConfigurationItem:
        ci.changes.add(change)
        return ci

    @staticmethod
    @transaction.atomic
    def unlink_change(ci: ConfigurationItem, change) -> ConfigurationItem:
        ci.changes.remove(change)
        return ci
