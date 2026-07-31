from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.service_desk.api.views import KnowledgeViewSet

router = DefaultRouter()
router.register(r"articles", KnowledgeViewSet, basename="api-gw-knowledge")

urlpatterns = router.urls
