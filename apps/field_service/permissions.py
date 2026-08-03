from rest_framework.permissions import IsAuthenticated


class IsFieldTechnician(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_staff or hasattr(request.user, "agent_profile")
        )
