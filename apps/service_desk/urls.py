<<<<<<< HEAD
from django.urls import path

from . import views
=======
"""URL routes for the Service Desk application."""
>>>>>>> 43f299f104a26a02e672f1ae2b81774211179472

from django.urls import include, path

from apps.service_desk import views

app_name = "service_desk"

urlpatterns = [
<<<<<<< HEAD

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "tickets/",
        views.ticket_list,
        name="ticket_list",
    ),

    path(
        "tickets/create/",
        views.ticket_create,
        name="ticket_create",
    ),

    path(
        "tickets/<int:pk>/",
        views.ticket_detail,
        name="ticket_detail",
    ),

    path(
        "tickets/<int:pk>/edit/",
        views.ticket_update,
        name="ticket_update",
    ),

    path(
        "tickets/<int:pk>/delete/",
        views.ticket_delete,
        name="ticket_delete",
    ),

]
=======
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard_alt"),
    # Tickets
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/update/", views.ticket_update, name="ticket_update"),
    path("tickets/<int:pk>/comment/", views.ticket_comment, name="ticket_comment"),
    path("tickets/<int:pk>/worklog/", views.ticket_worklog, name="ticket_worklog"),
    path("tickets/<int:pk>/assign/", views.ticket_assign, name="ticket_assign"),
    path("tickets/<int:pk>/attach/", views.ticket_attach, name="ticket_attach"),
    path("tickets/<int:pk>/feedback/", views.ticket_feedback, name="ticket_feedback"),
    # Knowledge
    path("knowledge/", views.knowledge_list, name="knowledge_list"),
    path("knowledge/new/", views.knowledge_create, name="knowledge_create"),
    path("knowledge/<slug:slug>/", views.knowledge_detail, name="knowledge_detail"),
    path(
        "knowledge/<slug:slug>/feedback/",
        views.knowledge_feedback,
        name="knowledge_feedback",
    ),
    # Assets
    path("assets/", views.asset_list, name="asset_list"),
    path("assets/new/", views.asset_create, name="asset_create"),
    path("assets/<int:pk>/", views.asset_detail, name="asset_detail"),
    # Reports / notifications
    path("reports/", views.reports_index, name="reports"),
    path("notifications/", views.notification_list, name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.notification_read,
        name="notification_read",
    ),
    path("api/dashboard/", views.api_dashboard_json, name="api_dashboard"),
    # DRF API
    path("api/v1/", include("apps.service_desk.api.urls")),
]

# Legacy namespace alias expected by older tests
ticketing_urlpatterns = [
    path("tickets/", views.ticket_list, name="ticket_list"),
]
>>>>>>> 43f299f104a26a02e672f1ae2b81774211179472
