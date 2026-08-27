from apps.service_desk.views.sla import (
    SLAPolicyListView,
    SLAPolicyCreateView,
    SLABreachListView,
)
from django.urls import include, path

from apps.service_desk.views import (
    DashboardView,
    TicketListView,
    TicketCreateView,
    TicketDetailView,
    TicketAssignView,
    TicketStatusChangeView,
    TicketRequestConfirmationView,
    TicketCommentView,
    TicketWorkNoteView,
    TicketAttachmentUploadView,
    TicketAttachmentDownloadView,
    TicketCloseView,
    TicketReopenView,
    IncidentDashboardView,
    ProblemListView,
    ProblemCreateView,
    ProblemDetailView,
    ProblemAssignView,
    ProblemStatusChangeView,
    ProblemRootCauseView,
    ProblemWorkaroundView,
    ProblemMarkKnownErrorView,
    ProblemCommentView,
    ProblemLinkTicketView,
    ProblemUnlinkTicketView,
    ProblemCloseView,
    ProblemReopenView,
    SupplierListView,
    SupplierCreateView,
    SupplierDetailView,
)

app_name = "service_desk"

urlpatterns = [
    path('sla/', include(('apps.service_desk.sla.urls', 'sla'), namespace='sla')),
    path("", DashboardView.as_view(), name="dashboard"),

    path("tickets/", TicketListView.as_view(), name="ticket_list"),
    path("tickets/new/", TicketCreateView.as_view(), name="ticket_create"),
    path("tickets/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
    path("tickets/<int:pk>/assign/", TicketAssignView.as_view(), name="ticket_assign"),
    path("tickets/<int:pk>/status/", TicketStatusChangeView.as_view(), name="ticket_status_change"),
    path("tickets/<int:pk>/request-confirmation/", TicketRequestConfirmationView.as_view(), name="ticket_request_confirmation"),
    path("tickets/<int:pk>/comment/", TicketCommentView.as_view(), name="ticket_comment"),
    path("tickets/<int:pk>/work-note/", TicketWorkNoteView.as_view(), name="ticket_work_note"),
    path("tickets/<int:pk>/attach/", TicketAttachmentUploadView.as_view(), name="ticket_attach"),
    path("tickets/<int:pk>/attachments/<int:attachment_pk>/", TicketAttachmentDownloadView.as_view(), name="ticket_attachment_download"),
    path("tickets/<int:pk>/close/", TicketCloseView.as_view(), name="ticket_close"),
    path("tickets/<int:pk>/reopen/", TicketReopenView.as_view(), name="ticket_reopen"),

    path("incidents/", IncidentDashboardView.as_view(), name="incident_dashboard"),

    path("problems/", ProblemListView.as_view(), name="problem_list"),
    path("problems/new/", ProblemCreateView.as_view(), name="problem_create"),
    path("problems/<int:pk>/", ProblemDetailView.as_view(), name="problem_detail"),
    path("problems/<int:pk>/assign/", ProblemAssignView.as_view(), name="problem_assign"),
    path("problems/<int:pk>/status/", ProblemStatusChangeView.as_view(), name="problem_status_change"),
    path("problems/<int:pk>/comment/", ProblemCommentView.as_view(), name="problem_comment"),
    path("problems/<int:pk>/root-cause/", ProblemRootCauseView.as_view(), name="problem_root_cause"),
    path("problems/<int:pk>/workaround/", ProblemWorkaroundView.as_view(), name="problem_workaround"),
    path("problems/<int:pk>/known-error/", ProblemMarkKnownErrorView.as_view(), name="problem_mark_known_error"),
    path("problems/<int:pk>/link-ticket/", ProblemLinkTicketView.as_view(), name="problem_link_ticket"),
    path("problems/<int:pk>/unlink-ticket/<int:ticket_pk>/", ProblemUnlinkTicketView.as_view(), name="problem_unlink_ticket"),
    path("problems/<int:pk>/close/", ProblemCloseView.as_view(), name="problem_close"),
    path("problems/<int:pk>/reopen/", ProblemReopenView.as_view(), name="problem_reopen"),

    path("suppliers/", SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/new/", SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/", SupplierDetailView.as_view(), name="supplier_detail"),

    path(
        "change/",
        include("apps.service_desk.urls.change_management"),
    ),
    path(
        "release/",
        include("apps.service_desk.urls.release_management"),
    ),
]





