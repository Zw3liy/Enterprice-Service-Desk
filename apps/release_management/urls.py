from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.release_management import views

app_name = "releases"

router = DefaultRouter()
router.register(r"releases", views.ReleaseViewSet, basename="api-release")

urlpatterns = [
    path("", views.release_list, name="list"),
    path("new/", views.release_create, name="create"),
    path("<int:pk>/", views.release_detail, name="detail"),
    path("<int:pk>/transition/", views.release_transition, name="transition"),
    path("api/", include(router.urls)),
]