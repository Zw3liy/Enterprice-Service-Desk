from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsIncidentAgent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return bool(user.is_staff or hasattr(user, "agent_profile"))