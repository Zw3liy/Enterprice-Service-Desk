from django.urls import path

from apps.executive_dashboard import views

app_name = "executive"

urlpatterns = [
    path("", views.executive_home, name="home"),
    path("api/board/", views.ExecutiveBoardAPI.as_view(), name="api-board"),
]
