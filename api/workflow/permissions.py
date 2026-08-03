from rest_framework.permissions import IsAuthenticated


class IsWorkflowAgent(IsAuthenticated):
    def has_permission(self, request, view):
        ok = super().has_permission(request, view)
        return ok and (request.user.is_staff or hasattr(request.user, "agent_profile"))
