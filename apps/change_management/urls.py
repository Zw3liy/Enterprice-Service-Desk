from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.change_management import views

app_name = "changes"

router = DefaultRouter()
router.register(r"changes", views.ChangeViewSet, basename="api-change")
router.register(r"cab", views.CABMeetingViewSet, basename="api-cab")

urlpatterns = [
    path("", views.change_list, name="list"),
    path("new/", views.change_create, name="create"),
    path("cab/", views.cab_list, name="cab_list"),
    path("<int:pk>/", views.change_detail, name="detail"),
    path("<int:pk>/submit/", views.change_submit, name="submit"),
    path("<int:pk>/request-approval/", views.change_request_approval, name="request_approval"),
    path("<int:pk>/decide/", views.change_decide, name="decide"),
    path("api/", include(router.urls)),
]