from django.urls import path

from apps.service_desk.sla import views

urlpatterns = [
    path("", views.sla_list, name="sla_list"),
]
