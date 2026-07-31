from django.urls import path

from apps.service_desk.automation import views

urlpatterns = [
    path("", views.automation_home, name="automation_home"),
]
