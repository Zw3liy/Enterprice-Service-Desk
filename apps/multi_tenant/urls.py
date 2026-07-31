from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.multi_tenant import views

app_name = "multi_tenant"

router = DefaultRouter()
router.register(r"domains", views.TenantDomainViewSet, basename="api-tenant-domain")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/tenants/", views.TenantListAPI.as_view(), name="api-tenants"),
    path("api/provision/", views.TenantProvisionAPI.as_view(), name="api-provision"),
    path("api/settings/", views.TenantSettingsAPI.as_view(), name="api-settings"),
]
