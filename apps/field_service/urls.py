from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.field_service import views

app_name = "field_service"

router = DefaultRouter()
router.register(r"work-orders", views.WorkOrderViewSet, basename="api-work-order")

urlpatterns = [
    path("api/", include(router.urls)),
]
