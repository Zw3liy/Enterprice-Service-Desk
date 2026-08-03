"""RBAC role assignments stored per company."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class RoleDefinition(TimeStampedModel):
    """Named enterprise role with permission codenames."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="role_definitions",
        null=True,
        blank=True,
        help_text="Null company = global system role template.",
    )
    code = models.SlugField(max_length=60)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    permissions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of permission codenames, e.g. can_assign_ticket.",
    )
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="rbac_role_company_code_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name


class UserRoleAssignment(TimeStampedModel):
    """Assign a role definition to a user within a company."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="user_role_assignments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="esd_role_assignments",
    )
    role = models.ForeignKey(
        RoleDefinition, on_delete=models.CASCADE, related_name="assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user", "role"],
                name="rbac_user_role_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.role.code}"
