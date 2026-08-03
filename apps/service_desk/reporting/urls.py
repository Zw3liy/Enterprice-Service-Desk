from django.urls import path

from apps.service_desk.reporting import views
from apps.service_desk.views import reports_index

urlpatterns = [
    path("", reports_index, name="reporting_home"),
    path("export/tickets.csv", views.export_tickets, name="export_tickets"),
]
