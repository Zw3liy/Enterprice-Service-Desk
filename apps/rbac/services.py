"""Role-based access control application services."""

from __future__ import annotations

import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.rbac.models import RoleDefinition, UserRoleAssignment
from apps.rbac.roles import ALL_ROLES, DEFAULT_ROLE_PERMISSIONS, ROLE_ADMIN, ROLE_AGENT
from apps.service_desk.identity.roles import resolve_roles
from apps.service_desk.models import Ticket

logger = logging.getLogger(__name__)


class RBACService:
    ROLE_GROUP_MAP = {
        "admin": "ESD Administrators",
        "agent": "ESD Agents",
        "requester": "ESD Requesters",
        "approver": "ESD Approvers",
        "cab_member": "ESD CAB Members",
    }

    @classmethod
    def ensure_groups(cls) -> dict[str, Group]:
        groups: dict[str, Group] = {}
        for role, name in cls.ROLE_GROUP_MAP.items():
            group, _ = Group.objects.get_or_create(name=name)
            groups[role] = group
        ct = ContentType.objects.get_for_model(Ticket)
        perms = Permission.objects.filter(content_type=ct)
        groups["admin"].permissions.set(perms)
        agent_codes = set(DEFAULT_ROLE_PERMISSIONS.get(ROLE_AGENT, []))
        groups["agent"].permissions.set(perms.filter(codename__in=agent_codes))
        return groups

    @classmethod
    @transaction.atomic
    def ensure_role_definitions(cls, company=None) -> list[RoleDefinition]:
        created = []
        for code in ALL_ROLES:
            role, was_created = RoleDefinition.objects.get_or_create(
                company=company,
                code=code,
                defaults={
                    "name": code.replace("_", " ").title(),
                    "description": f"System role: {code}",
                    "permissions": DEFAULT_ROLE_PERMISSIONS.get(code, []),
                    "is_system": True,
                    "is_active": True,
                },
            )
            if was_created:
                created.append(role)
        return created

    @classmethod
    def assign_role(cls, user, role: str, company=None, assigned_by=None) -> Group | RoleDefinition:
        if role not in ALL_ROLES:
            raise ValueError(f"Unknown role: {role}")
        groups = cls.ensure_groups()
        group = groups[role]
        user.groups.add(group)
        if role == ROLE_ADMIN and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        if company is not None:
            cls.ensure_role_definitions(company)
            role_def = RoleDefinition.objects.get(company=company, code=role)
            UserRoleAssignment.objects.update_or_create(
                company=company,
                user=user,
                role=role_def,
                defaults={"is_active": True, "assigned_by": assigned_by},
            )
            return role_def
        return group

    @staticmethod
    def user_roles(user) -> list[str]:
        roles = set(resolve_roles(user))
        if user and user.is_authenticated:
            for assignment in UserRoleAssignment.objects.filter(
                user=user, is_active=True
            ).select_related("role"):
                roles.add(assignment.role.code)
        return list(roles)

    @staticmethod
    def has_role(user, role: str) -> bool:
        return role in RBACService.user_roles(user)

    @staticmethod
    def has_permission(user, codename: str, company=None) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.has_perm(f"service_desk.{codename}") or user.has_perm(codename):
            return True
        qs = UserRoleAssignment.objects.filter(user=user, is_active=True).select_related(
            "role"
        )
        if company is not None:
            qs = qs.filter(company=company)
        for assignment in qs:
            if codename in (assignment.role.permissions or []):
                return True
        return False
