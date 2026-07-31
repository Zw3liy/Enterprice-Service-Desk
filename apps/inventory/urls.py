from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory import views

app_name = "inventory"

router = DefaultRouter()
router.register(r"warehouses", views.WarehouseViewSet, basename="api-warehouse")
router.register(r"items", views.StockItemViewSet, basename="api-stock-item")
router.register(r"movements", views.StockMovementViewSet, basename="api-stock-movement")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/move/", views.StockMoveAPI.as_view(), name="api-move"),
    path("api/reorder/", views.InventoryReorderAPI.as_view(), name="api-reorder"),
]
