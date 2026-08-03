from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.rbac import views

app_name = "rbac"

router = DefaultRouter()
router.register(r"roles", views.RoleDefinitionViewSet, basename="api-rbac-role")
router.register(r"assignments", views.UserRoleAssignmentViewSet, basename="api-rbac-assignment")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/me/", views.RBACMeAPI.as_view(), name="api-me"),
    path("api/assign/", views.RBACAssignAPI.as_view(), name="api-assign"),
    path("api/bootstrap/", views.RBACBootstrapAPI.as_view(), name="api-bootstrap"),
]
