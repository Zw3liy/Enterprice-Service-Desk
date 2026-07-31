from rest_framework.permissions import BasePermission

from apps.rbac.services import RBACService
from apps.service_desk.identity.roles import ROLE_ADMIN, ROLE_AGENT


class HasESDRole(BasePermission):
    required_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        roles = set(RBACService.user_roles(request.user))
        return bool(roles.intersection(self.required_roles))


class IsESDAgent(HasESDRole):
    required_roles = (ROLE_AGENT, ROLE_ADMIN)


class IsESDAdmin(HasESDRole):
    required_roles = (ROLE_ADMIN,)
