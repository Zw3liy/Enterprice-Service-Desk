from django.urls import path

from apps.offline_sync import views

app_name = "offline_sync"

urlpatterns = [
    path("api/pull/", views.SyncPullAPI.as_view(), name="api-pull"),
    path("api/push/", views.SyncPushAPI.as_view(), name="api-push"),
]
