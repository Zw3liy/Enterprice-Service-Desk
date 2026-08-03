from django.urls import path
from . import views


urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard"
    ),
    path(
        "tickets/new/",
        views.ticket_create,
        name="ticket_create"
    ),
]
