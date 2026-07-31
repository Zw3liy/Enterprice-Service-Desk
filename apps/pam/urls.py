from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.pam import views

app_name = "pam"

router = DefaultRouter()
router.register(r"accounts", views.PrivilegedAccountViewSet, basename="api-pam-account")
router.register(r"requests", views.AccessRequestViewSet, basename="api-pam-request")
router.register(r"sessions", views.PrivilegedSessionViewSet, basename="api-pam-session")

urlpatterns = [
    path("api/", include(router.urls)),
]
