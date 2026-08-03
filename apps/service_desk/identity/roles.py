"""Role constants for ESD RBAC."""

ROLE_ADMIN = "admin"
ROLE_AGENT = "agent"
ROLE_REQUESTER = "requester"
ROLE_APPROVER = "approver"
ROLE_CAB = "cab_member"

ALL_ROLES = (ROLE_ADMIN, ROLE_AGENT, ROLE_REQUESTER, ROLE_APPROVER, ROLE_CAB)


def resolve_roles(user) -> list[str]:
    roles = []
    if not user or not user.is_authenticated:
        return roles
    if user.is_superuser or user.is_staff:
        roles.append(ROLE_ADMIN)
        roles.append(ROLE_AGENT)
    if hasattr(user, "agent_profile"):
        roles.append(ROLE_AGENT)
    if hasattr(user, "service_desk_contact"):
        roles.append(ROLE_REQUESTER)
    return list(dict.fromkeys(roles))
