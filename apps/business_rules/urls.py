from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.business_rules import views

app_name = "business_rules"

router = DefaultRouter()
router.register(r"rules", views.BusinessRuleViewSet, basename="api-business-rule")

urlpatterns = [
    path("api/", include(router.urls)),
]
