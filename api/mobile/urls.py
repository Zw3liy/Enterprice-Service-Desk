from django.urls import path

from api.mobile.views import MobileBootstrapAPI, MobileTicketListAPI

urlpatterns = [
    path("bootstrap/", MobileBootstrapAPI.as_view(), name="api-mobile-bootstrap"),
    path("tickets/", MobileTicketListAPI.as_view(), name="api-mobile-tickets"),
]
