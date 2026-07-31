from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.incident_management import views

app_name = "incidents"

router = DefaultRouter()
router.register(r"incidents", views.IncidentViewSet, basename="api-incident")

urlpatterns = [
    path("", views.incident_list, name="list"),
    path("new/", views.incident_create, name="create"),
    path("<int:pk>/", views.incident_detail, name="detail"),
    path("<int:pk>/major/", views.declare_major, name="declare_major"),
    path("<int:pk>/timeline/", views.add_timeline, name="add_timeline"),
    path("api/", include(router.urls)),
    path("api/major/", views.MajorIncidentListAPI.as_view(), name="api-major"),
]