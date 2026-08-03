from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.form_builder import views

app_name = "form_builder"

router = DefaultRouter()
router.register(r"forms", views.FormDefinitionViewSet, basename="api-form")
router.register(r"submissions", views.FormSubmissionViewSet, basename="api-form-submission")

urlpatterns = [
    path("api/", include(router.urls)),
]
