from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.vendor_management import views

app_name = "vendors"

router = DefaultRouter()
router.register(r"vendors", views.VendorViewSet, basename="api-vendor")
router.register(r"contracts", views.VendorContractViewSet, basename="api-vendor-contract")

urlpatterns = [
    path("", views.vendor_list, name="list"),
    path("new/", views.vendor_create, name="create"),
    path("<int:pk>/", views.vendor_detail, name="detail"),
    path("api/", include(router.urls)),
]