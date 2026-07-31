from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.procurement import views

app_name = "procurement"

router = DefaultRouter()
router.register(r"requests", views.PurchaseRequestViewSet, basename="api-pr")
router.register(r"orders", views.PurchaseOrderViewSet, basename="api-po")

urlpatterns = [
    path("api/", include(router.urls)),
]
