from django.urls import path

from apps.service_desk.views.change_management import (
    change_action,
    change_create,
    change_detail,
    change_list,
)


app_name = "change_management"


urlpatterns = [
    path("", change_list, name="list"),
    path("new/", change_create, name="create"),
    path("<int:pk>/", change_detail, name="detail"),
    path("<int:pk>/<str:action>/", change_action, name="action"),
]

