from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.problem_management import views

app_name = "problems"

router = DefaultRouter()
router.register(r"problems", views.ProblemViewSet, basename="api-problem")

urlpatterns = [
    path("", views.problem_list, name="list"),
    path("new/", views.problem_create, name="create"),
    path("<int:pk>/", views.problem_detail, name="detail"),
    path("<int:pk>/root-cause/", views.set_root_cause, name="root_cause"),
    path("<int:pk>/link/", views.link_incident, name="link_incident"),
    path("api/", include(router.urls)),
]