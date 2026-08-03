from django.urls import path

from apps.forecasting import views

app_name = "forecasting"

urlpatterns = [
    path("api/tickets/", views.TicketForecastAPI.as_view(), name="api-ticket-forecast"),
    path("api/staffing/", views.StaffingForecastAPI.as_view(), name="api-staffing-forecast"),
]
