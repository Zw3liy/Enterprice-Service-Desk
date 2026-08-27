from .views import IncidentDashboardView
from django.urls import path
from . import views

app_name = 'service_desk'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/new/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
]