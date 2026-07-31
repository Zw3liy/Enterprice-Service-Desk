from rest_framework.permissions import IsAuthenticated


class IsReleaseManager(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_staff or request.user.is_superuser
        )
