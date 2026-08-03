"""Canonical role codes for Enterprise Service Desk."""

from apps.service_desk.identity.roles import (
    ALL_ROLES,
    ROLE_ADMIN,
    ROLE_AGENT,
    ROLE_APPROVER,
    ROLE_CAB,
    ROLE_REQUESTER,
    resolve_roles,
)

__all__ = [
    "ALL_ROLES",
    "ROLE_ADMIN",
    "ROLE_AGENT",
    "ROLE_APPROVER",
    "ROLE_CAB",
    "ROLE_REQUESTER",
    "resolve_roles",
]

DEFAULT_ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "add_ticket",
        "change_ticket",
        "delete_ticket",
        "view_ticket",
        "can_assign_ticket",
        "can_escalate_ticket",
        "can_view_internal_comments",
        "can_manage_sla",
    ],
    ROLE_AGENT: [
        "add_ticket",
        "change_ticket",
        "view_ticket",
        "can_assign_ticket",
        "can_view_internal_comments",
        "can_escalate_ticket",
    ],
    ROLE_REQUESTER: ["add_ticket", "view_ticket"],
    ROLE_APPROVER: ["view_ticket", "change_ticket"],
    ROLE_CAB: ["view_ticket", "change_ticket", "can_view_internal_comments"],
}
