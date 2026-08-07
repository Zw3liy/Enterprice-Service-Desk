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
    path('tickets/<int:pk>/request-confirmation/', views.TicketRequestConfirmationView.as_view(), name='ticket_request_confirmation'),
    path('tickets/<int:pk>/comment/', views.TicketCommentView.as_view(), name='ticket_comment'),
    path('tickets/<int:pk>/work-note/', views.TicketWorkNoteView.as_view(), name='ticket_work_note'),
    path('tickets/<int:pk>/attach/', views.TicketAttachmentUploadView.as_view(), name='ticket_attach'),
    path('tickets/<int:pk>/attachments/<int:attachment_pk>/', views.TicketAttachmentDownloadView.as_view(), name='ticket_attachment_download'),
    path('tickets/<int:pk>/close/', views.TicketCloseView.as_view(), name='ticket_close'),
    path('tickets/<int:pk>/reopen/', views.TicketReopenView.as_view(), name='ticket_reopen'),
    path('incidents/', views.IncidentDashboardView.as_view(), name='incident_dashboard'),
    path('problems/', views.ProblemListView.as_view(), name='problem_list'),
    path('problems/new/', views.ProblemCreateView.as_view(), name='problem_create'),
    path('problems/<int:pk>/', views.ProblemDetailView.as_view(), name='problem_detail'),
    path('problems/<int:pk>/assign/', views.ProblemAssignView.as_view(), name='problem_assign'),
    path('problems/<int:pk>/status/', views.ProblemStatusChangeView.as_view(), name='problem_status_change'),
    path('problems/<int:pk>/comment/', views.ProblemCommentView.as_view(), name='problem_comment'),
    path('problems/<int:pk>/root-cause/', views.ProblemRootCauseView.as_view(), name='problem_root_cause'),
    path('problems/<int:pk>/workaround/', views.ProblemWorkaroundView.as_view(), name='problem_workaround'),
    path('problems/<int:pk>/known-error/', views.ProblemMarkKnownErrorView.as_view(), name='problem_mark_known_error'),
    path('problems/<int:pk>/link-ticket/', views.ProblemLinkTicketView.as_view(), name='problem_link_ticket'),
    path('problems/<int:pk>/unlink-ticket/<int:ticket_pk>/', views.ProblemUnlinkTicketView.as_view(), name='problem_unlink_ticket'),
    path('problems/<int:pk>/close/', views.ProblemCloseView.as_view(), name='problem_close'),
    path('problems/<int:pk>/reopen/', views.ProblemReopenView.as_view(), name='problem_reopen'),
]