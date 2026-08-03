from django.urls import path

from apps.service_desk import views

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("<int:pk>/read/", views.notification_read, name="notification_mark_read"),
]
