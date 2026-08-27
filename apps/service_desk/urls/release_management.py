from django.urls import path

from apps.service_desk.views.release_management import (
    release_create,
    release_detail,
    release_execute,
    release_list,
    release_rollback,
    release_schedule,
)

app_name = "release_management"

urlpatterns = [
    path("", release_list, name="list"),
    path("create/", release_create, name="create"),
    path("<int:pk>/", release_detail, name="detail"),
    path("<int:pk>/schedule/", release_schedule, name="schedule"),
    path("<int:pk>/execute/", release_execute, name="execute"),
    path("<int:pk>/rollback/", release_rollback, name="rollback"),
]
