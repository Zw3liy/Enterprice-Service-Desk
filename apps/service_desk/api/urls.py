"""API v1 router."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.service_desk.api import views

router = DefaultRouter()
router.register(r"companies", views.CompanyViewSet, basename="api-company")
router.register(r"departments", views.DepartmentViewSet, basename="api-department")
router.register(r"categories", views.CategoryViewSet, basename="api-category")
router.register(r"priorities", views.PriorityViewSet, basename="api-priority")
router.register(r"statuses", views.StatusViewSet, basename="api-status")
router.register(r"queues", views.QueueViewSet, basename="api-queue")
router.register(r"request-types", views.RequestTypeViewSet, basename="api-request-type")
router.register(r"slas", views.SLAViewSet, basename="api-sla")
router.register(r"tickets", views.TicketViewSet, basename="api-ticket")
router.register(r"assets", views.AssetViewSet, basename="api-asset")
router.register(r"knowledge", views.KnowledgeViewSet, basename="api-knowledge")
router.register(r"notifications", views.NotificationViewSet, basename="api-notification")
router.register(r"audit", views.AuditLogViewSet, basename="api-audit")

urlpatterns = [
    path("", views.api_root, name="api-root"),
    path("dashboard/", views.DashboardAPIView.as_view(), name="api-dashboard-v1"),
    path("ai/classify/", views.AIClassifyAPIView.as_view(), name="api-ai-classify"),
    path("", include(router.urls)),
]
