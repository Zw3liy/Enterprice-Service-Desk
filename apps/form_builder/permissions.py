from rest_framework.permissions import IsAuthenticated


class IsFormDesigner(IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return super().has_permission(request, view)
        return super().has_permission(request, view) and request.user.is_staff
