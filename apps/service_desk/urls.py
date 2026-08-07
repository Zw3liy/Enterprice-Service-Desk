from django.urls import path
from . import views

app_name = 'service_desk'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/new/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<int:pk>/assign/', views.TicketAssignView.as_view(), name='ticket_assign'),
    path('tickets/<int:pk>/status/', views.TicketStatusChangeView.as_view(), name='ticket_status_change'),
    path('tickets/<int:pk>/comment/', views.TicketCommentView.as_view(), name='ticket_comment'),
    path('tickets/<int:pk>/close/', views.TicketCloseView.as_view(), name='ticket_close'),
    path('tickets/<int:pk>/reopen/', views.TicketReopenView.as_view(), name='ticket_reopen'),
    path('incidents/', views.IncidentDashboardView.as_view(), name='incident_dashboard'),
]