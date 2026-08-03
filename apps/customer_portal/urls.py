from django.urls import path

from apps.customer_portal import views

app_name = "portal"

urlpatterns = [
    path("", views.portal_home, name="home"),
    path("tickets/", views.portal_tickets, name="tickets"),
    path("tickets/new/", views.portal_new_request, name="new_request"),
    path("tickets/<int:pk>/", views.portal_ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/comment/", views.portal_comment, name="comment"),
    path("catalog/", views.portal_catalog, name="catalog"),
    path("knowledge/", views.portal_knowledge, name="knowledge"),
    path("api/", views.PortalHomeAPI.as_view(), name="api-home"),
    path("api/tickets/", views.PortalTicketAPI.as_view(), name="api-tickets"),
    path("api/tickets/<int:pk>/", views.PortalTicketAPI.as_view(), name="api-ticket-detail"),
]