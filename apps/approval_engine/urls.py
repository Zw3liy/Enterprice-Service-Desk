from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.approval_engine import views

app_name = "approvals"

router = DefaultRouter()
router.register(r"policies", views.ApprovalPolicyViewSet, basename="api-approval-policy")
router.register(r"inbox", views.ApprovalInboxViewSet, basename="api-approval-inbox")

urlpatterns = [
    path("api/", include(router.urls)),
]
