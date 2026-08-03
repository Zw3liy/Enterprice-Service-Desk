from django.urls import path

from api.tenant.views import TenantProvisionAPI, TenantListAPI

urlpatterns = [
    path("", TenantListAPI.as_view(), name="api-tenant-list"),
    path("provision/", TenantProvisionAPI.as_view(), name="api-tenant-provision"),
]
