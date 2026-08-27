"""
apps/service_desk/views.py

Enterprise Service Desk
Phase 2.2.4 ΓÇö Authorization Hardening
"""


from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    DetailView,
)

from .models import Problem, Supplier, Ticket, TicketAttachment, TicketHistory
from .forms.ticket_forms import TicketCreateForm
from .forms.problem_forms import ProblemCreateForm
from .forms.supplier_forms import SupplierCreateForm

from .security.policies import (
    get_problem_queryset,
    get_supplier_queryset,
    get_ticket_queryset,
)
from .security.mixins import (
    TicketPermissionMixin,
    TicketChangePermissionMixin,
    TicketViewPermissionMixin,
    ProblemPermissionMixin,
    ProblemViewPermissionMixin,
    ProblemCreatePermissionMixin,
    ProblemChangePermissionMixin,
    SupplierCreatePermissionMixin,
    SupplierViewPermissionMixin,
)
from .selectors.ticket_selector import TicketSelector
from .selectors.problem_selector import ProblemSelector
from .selectors.supplier_selector import SupplierSelector
from .services.ticket_service import TicketService
from .services.problem_service import ProblemService
from .services.supplier_service import SupplierService

User = get_user_model()



# --------------------------------------------------
# Dashboard
# --------------------------------------------------

class DashboardView(
    TicketPermissionMixin,
    TemplateView
):
    """
    Main dashboard.

    Authentication required.
    """

    template_name = "service_desk/dashboard.html"

    permission_required = (
        "service_desk.view_ticket"
    )



# --------------------------------------------------
# Ticket List
# --------------------------------------------------

class TicketListView(
    TicketPermissionMixin,
    ListView
):
    """
    Ticket listing.

    Visibility controlled by:
        security.policies.get_ticket_queryset()

    Rules:
        Requester:
            own tickets

        Technician:
            assigned tickets

        Manager:
            department tickets

        Administrator:
            all tickets
    """

    model = Ticket

    template_name = (
        "tickets/ticket_list.html"
    )

    context_object_name = "tickets"

    permission_required = (
        "service_desk.view_ticket"
    )


    def get_queryset(self):

        return get_ticket_queryset(
            self.request.user
        )



# --------------------------------------------------
# Ticket Create
# --------------------------------------------------

class TicketCreateView(
    TicketPermissionMixin,
    CreateView
):
    """
    Ticket creation.

    Requires:
        service_desk.add_ticket

    Automatically assigns:
        created_by = logged in user
    """

    model = Ticket

    form_class = TicketCreateForm

    template_name = (
        "tickets/create.html"
    )

    permission_required = (
        "service_desk.add_ticket"
    )


    success_url = reverse_lazy(
        "service_desk:ticket_list"
    )


    def form_valid(self, form):

        self.object = TicketService.create_ticket(
            created_by=self.request.user,
            **form.cleaned_data,
        )

        return redirect(self.get_success_url())



# --------------------------------------------------
# Ticket Detail
# --------------------------------------------------

class TicketDetailView(
    TicketPermissionMixin,
    DetailView
):
    """
    Ticket detail view.

    Object visibility is enforced
    through queryset filtering.
    """

    model = Ticket

    template_name = (
        "tickets/detail.html"
    )

    context_object_name = (
        "ticket"
    )

    permission_required = (
        "service_desk.view_ticket"
    )


    def get_queryset(self):

        return get_ticket_queryset(
            self.request.user
        )


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        history_qs = self.object.history.select_related(
            "performed_by"
        ).order_by("-created_at")

        # Work notes are filtered out for Requesters (users without
        # change_ticket) ΓÇö ADR-010, Decision 3.
        if not self.request.user.has_perm("service_desk.change_ticket"):
            history_qs = history_qs.exclude(
                event_type=TicketHistory.EVENT_WORK_NOTE,
            )

        context["history"] = history_qs

        context["attachments"] = self.object.attachments.select_related(
            "uploaded_by"
        ).order_by("-uploaded_at")

        context["available_technicians"] = User.objects.filter(
            groups__name="Technician",
            is_active=True,
        ).order_by("username")

        status_labels = dict(Ticket.STATUS_CHOICES)

        context["next_statuses"] = [
            (status, status_labels.get(status, status))
            for status in TicketService.STATUS_FLOW.get(
                self.object.status, []
            )
        ]

        return context



# --------------------------------------------------
# Ticket Assignment
# --------------------------------------------------

class TicketAssignView(
    TicketChangePermissionMixin,
    View
):
    """
    Assign (or reassign) a ticket to a technician.

    Requires:
        service_desk.change_ticket
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        technician = get_object_or_404(
            User,
            pk=request.POST.get("technician_id"),
            is_active=True,
        )

        try:
            TicketService.assign_ticket(
                ticket,
                technician,
                user=request.user,
            )
            messages.success(
                request,
                f"Ticket assigned to {technician.get_username()}.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)



# --------------------------------------------------
# Ticket Status Change
# --------------------------------------------------

class TicketStatusChangeView(
    TicketChangePermissionMixin,
    View
):
    """
    Move a ticket through its validated status lifecycle.

    Requires:
        service_desk.change_ticket

    Invalid transitions are rejected by
    TicketService.change_status and surfaced as a message
    rather than a hard error, since this is a user-facing form.
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        status = request.POST.get("status", "")

        try:
            TicketService.change_status(
                ticket,
                status,
                user=request.user,
            )
            messages.success(request, "Ticket status updated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)


# --------------------------------------------------
# Ticket Request Confirmation
# --------------------------------------------------

class TicketRequestConfirmationView(
    TicketChangePermissionMixin,
    View
):
    """
    Move a resolved ticket to 'awaiting_confirmation'.

    This is the Technician/Manager action that signals the
    resolution is ready for requester review. The actual
    close/confirm is done by the requester via
    TicketCloseView (ADR-010, Decision 3).

    Requires:
        service_desk.change_ticket
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        try:
            TicketService.change_status(
                ticket,
                "awaiting_confirmation",
                user=request.user,
            )
            messages.success(
                request,
                "Ticket sent for requester confirmation.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)



# --------------------------------------------------
# Ticket Comment
# --------------------------------------------------

class TicketCommentView(
    TicketViewPermissionMixin,
    View
):
    """
    Add a comment to a ticket.

    Requires:
        service_desk.view_ticket

    Any role that can see a ticket can comment on it ΓÇö there is
    currently no internal/external visibility distinction (see
    IM-03 design findings, docs/engineering/SESSION_STATE.md).
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        comment = request.POST.get("comment", "")

        try:
            TicketService.add_comment(
                ticket,
                comment,
                user=request.user,
            )
            messages.success(request, "Comment added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)


# --------------------------------------------------
# Ticket Work Note (internal ΓÇö Technician/Manager only)
# --------------------------------------------------

class TicketWorkNoteView(
    TicketChangePermissionMixin,
    View
):
    """
    Add an internal work note to a ticket.

    Requires:
        service_desk.change_ticket

    Work notes are never visible to Requesters ΓÇö the template
    filters them out for users lacking change_ticket (see
    ADR-010, Decision 3). This permission gate ensures only
    Technician/Manager/Admin can add them.
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        note = request.POST.get("work_note", "")

        try:
            TicketService.add_work_note(
                ticket,
                note,
                user=request.user,
            )
            messages.success(request, "Work note added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)


# --------------------------------------------------
# Ticket Attachment Upload
# --------------------------------------------------

class TicketAttachmentUploadView(
    TicketChangePermissionMixin,
    View
):
    """
    Upload a file attachment to a ticket.

    Requires:
        service_desk.change_ticket

    Only Technician/Manager/Admin can upload attachments.
    File extension and size are validated by TicketService.
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        uploaded_file = request.FILES.get("attachment")

        if not uploaded_file:
            messages.error(request, "No file selected.")
            return redirect("service_desk:ticket_detail", pk=ticket.pk)

        description = request.POST.get("description", "")

        try:
            TicketService.add_attachment(
                ticket,
                uploaded_file,
                user=request.user,
                description=description,
            )
            messages.success(request, "File attached successfully.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)


# --------------------------------------------------
# Ticket Attachment Download
# --------------------------------------------------

class TicketAttachmentDownloadView(
    TicketViewPermissionMixin,
    View
):
    """
    Download a ticket attachment.

    Requires:
        service_desk.view_ticket

    The attachment must belong to a ticket visible to the
    requesting user (RBAC-scoped queryset), ensuring
    Requesters can only download from their own tickets,
    Technicians from assigned/unassigned, etc.
    """

    def get(self, request, pk, attachment_pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        attachment = get_object_or_404(
            TicketAttachment,
            pk=attachment_pk,
            ticket=ticket,
        )

        try:
            return FileResponse(
                attachment.file.open("rb"),
                as_attachment=True,
                filename=attachment.original_filename or attachment.file.name,
            )
        except FileNotFoundError:
            raise Http404("Attachment file not found on disk.")



# --------------------------------------------------
# Ticket Close / Reopen
# --------------------------------------------------

class TicketCloseView(
    TicketViewPermissionMixin,
    View
):
    """
    Close a ticket after requester confirmation.

    Per ADR-010, Decision 3: the permission mixin is
    TicketViewPermissionMixin (view_ticket ΓÇö which Requesters
    hold) because the real gate is "are you the requester,"
    enforced in the service layer (change_status rejects
    non-requesters for the awaiting_confirmation ΓåÆ closed
    transition).
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        try:
            TicketService.close_ticket(ticket, user=request.user)
            messages.success(request, "Ticket closed. Resolution confirmed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)


class TicketReopenView(
    TicketChangePermissionMixin,
    View
):
    """
    Reopen a closed ticket.

    Requires:
        service_desk.change_ticket
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        try:
            TicketService.reopen_ticket(ticket, user=request.user)
            messages.success(request, "Ticket reopened.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:ticket_detail", pk=ticket.pk)



# --------------------------------------------------
# Incident Dashboard
# --------------------------------------------------

class IncidentDashboardView(TicketPermissionMixin, TemplateView):
    """
    Incident dashboard.

    Ticket is the incident record in this codebase (there is no
    separate Incident model) ΓÇö visibility is scoped through
    security.policies.get_ticket_queryset(), matching every other
    ticket view in this module.
    """

    template_name = "service_desk/incidents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        incidents = get_ticket_queryset(
            self.request.user
        ).select_related(
            "department",
            "assigned_to",
        )

        context.update({

            "incidents": incidents,

            "total_incidents":
                incidents.count(),

            "pending_incidents":
                TicketSelector.get_active_tickets(incidents),

            "resolved_incidents":
                TicketSelector.get_resolved_or_closed_tickets(incidents),

            "critical_incidents":
                TicketSelector.get_high_priority_tickets(incidents),

        })

        return context



# --------------------------------------------------
# Problem List
# --------------------------------------------------

class ProblemListView(
    ProblemPermissionMixin,
    ListView
):
    """
    Problem listing and dashboard.

    Visibility controlled by:
        security.policies.get_problem_queryset()

    Rules:
        Requester:
            none ΓÇö Requesters cannot access Problem records
            (ADR-010, Decision 1)

        Technician:
            assigned problems

        Manager:
            department problems

        Administrator:
            all problems

    Combines the list with dashboard-style stat cards (mirrors
    IncidentDashboardView) rather than shipping a separate
    dashboard view/route for a domain this size.
    """

    model = Problem

    template_name = "problems/list.html"

    context_object_name = "problems"

    permission_required = (
        "service_desk.view_problem"
    )


    def get_queryset(self):

        return get_problem_queryset(
            self.request.user
        )


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["stats"] = ProblemSelector.dashboard_statistics()

        return context



# --------------------------------------------------
# Supplier List


class SupplierListView(
    SupplierViewPermissionMixin,
    ListView
):
    """
    Supplier listing.

    Visibility controlled by:
        security.policies.get_supplier_queryset()
    """

    model = Supplier
    template_name = "suppliers/list.html"
    context_object_name = "suppliers"
    permission_required = (
        "service_desk.view_supplier",
    )


    def get_queryset(self):
        return get_supplier_queryset(self.request.user)


# --------------------------------------------------
# Supplier Create


class SupplierCreateView(
    SupplierCreatePermissionMixin,
    CreateView
):
    """
    Supplier creation.

    Requires:
        service_desk.add_supplier
    """

    model = Supplier
    form_class = SupplierCreateForm
    template_name = "suppliers/create.html"
    permission_required = (
        "service_desk.add_supplier",
    )


    success_url = reverse_lazy(
        "service_desk:supplier_list"
    )


    def form_valid(self, form):
        self.object = SupplierService.create_supplier(
            **form.cleaned_data,
        )

        return redirect(self.get_success_url())


# --------------------------------------------------
# Supplier Detail


class SupplierDetailView(
    SupplierViewPermissionMixin,
    DetailView
):
    """
    Supplier detail view.

    Object visibility is enforced through queryset filtering.
    """

    model = Supplier
    template_name = "suppliers/detail.html"
    context_object_name = "supplier"
    permission_required = (
        "service_desk.view_supplier",
    )


    def get_queryset(self):
        return get_supplier_queryset(self.request.user)


# --------------------------------------------------
# Problem Create
# --------------------------------------------------

class ProblemCreateView(
    ProblemCreatePermissionMixin,
    CreateView
):
    """
    Problem creation.

    Requires:
        service_desk.add_problem
    """

    model = Problem

    form_class = ProblemCreateForm

    template_name = "problems/create.html"

    permission_required = (
        "service_desk.add_problem"
    )


    success_url = reverse_lazy(
        "service_desk:problem_list"
    )


    def form_valid(self, form):

        self.object = ProblemService.create_problem(
            created_by=self.request.user,
            **form.cleaned_data,
        )

        return redirect(self.get_success_url())



# --------------------------------------------------
# Problem Detail
# --------------------------------------------------

class ProblemDetailView(
    ProblemPermissionMixin,
    DetailView
):
    """
    Problem detail view.

    Object visibility is enforced through queryset filtering.
    """

    model = Problem

    template_name = "problems/detail.html"

    context_object_name = "problem"

    permission_required = (
        "service_desk.view_problem"
    )


    def get_queryset(self):

        return get_problem_queryset(
            self.request.user
        )


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["history"] = self.object.history.select_related(
            "performed_by"
        ).order_by("-created_at")

        context["rca"] = getattr(self.object, "rca", None)

        context["available_investigators"] = User.objects.filter(
            groups__name="Technician",
            is_active=True,
        ).order_by("username")

        status_labels = dict(Problem.STATUS_CHOICES)

        context["next_statuses"] = [
            (status, status_labels.get(status, status))
            for status in ProblemService.STATUS_FLOW.get(
                self.object.status, []
            )
        ]

        context["repeat_incident_candidates"] = (
            ProblemSelector.repeat_incident_detection(self.object)
        )

        return context



# --------------------------------------------------
# Problem Assignment
# --------------------------------------------------

class ProblemAssignView(
    ProblemChangePermissionMixin,
    View
):
    """
    Assign (or reassign) a problem to an investigator.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        investigator = get_object_or_404(
            User,
            pk=request.POST.get("investigator_id"),
            is_active=True,
        )

        try:
            ProblemService.assign_problem(
                problem,
                investigator,
                user=request.user,
            )
            messages.success(
                request,
                f"Problem assigned to {investigator.get_username()}.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)



# --------------------------------------------------
# Problem Status Change
# --------------------------------------------------

class ProblemStatusChangeView(
    ProblemChangePermissionMixin,
    View
):
    """
    Move a problem through its validated status lifecycle.

    Requires:
        service_desk.change_problem

    Invalid transitions (and the known-error precondition) are
    rejected by ProblemService.change_status and surfaced as a
    message rather than a hard error.
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        status = request.POST.get("status", "")

        try:
            ProblemService.change_status(
                problem,
                status,
                user=request.user,
            )
            messages.success(request, "Problem status updated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)



# --------------------------------------------------
# Problem Root Cause / Workaround / Known Error
# --------------------------------------------------

class ProblemRootCauseView(
    ProblemChangePermissionMixin,
    View
):
    """
    Record or update a problem's root cause.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        root_cause = request.POST.get("root_cause", "")

        try:
            ProblemService.record_root_cause(
                problem,
                root_cause,
                user=request.user,
            )
            messages.success(request, "Root cause recorded.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)


class ProblemWorkaroundView(
    ProblemChangePermissionMixin,
    View
):
    """
    Record or update a problem's workaround.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        workaround = request.POST.get("workaround", "")

        try:
            ProblemService.record_workaround(
                problem,
                workaround,
                user=request.user,
            )
            messages.success(request, "Workaround recorded.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)


class ProblemMarkKnownErrorView(
    ProblemChangePermissionMixin,
    View
):
    """
    Declare a problem a Known Error.

    Requires:
        service_desk.change_problem

    Requires a RootCauseAnalysis to exist and root_cause to be
    populated ΓÇö enforced by ProblemService.mark_known_error.
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        try:
            ProblemService.mark_known_error(problem, user=request.user)
            messages.success(request, "Problem marked as Known Error.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)



# --------------------------------------------------
# Problem Comment
# --------------------------------------------------

class ProblemCommentView(
    ProblemViewPermissionMixin,
    View
):
    """
    Add a comment to a problem.

    Requires:
        service_desk.view_problem

    Requesters hold no Problem permissions at all (ADR-010,
    Decision 1), so this is effectively Technician/Manager/
    Administrator only despite the "view" permission name ΓÇö
    consistent with how TicketCommentView uses the view
    permission for Tickets, where Requesters legitimately can
    comment on their own tickets.
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        comment = request.POST.get("comment", "")

        try:
            ProblemService.add_comment(
                problem,
                comment,
                user=request.user,
            )
            messages.success(request, "Comment added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)



# --------------------------------------------------
# Problem Ticket Linking
# --------------------------------------------------

class ProblemLinkTicketView(
    ProblemChangePermissionMixin,
    View
):
    """
    Link a ticket to a problem.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=request.POST.get("ticket_id"),
        )

        try:
            ProblemService.link_ticket(
                problem,
                ticket,
                user=request.user,
            )
            messages.success(request, f"Linked {ticket}.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)


class ProblemUnlinkTicketView(
    ProblemChangePermissionMixin,
    View
):
    """
    Unlink a ticket from a problem.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk, ticket_pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=ticket_pk,
        )

        try:
            ProblemService.unlink_ticket(
                problem,
                ticket,
                user=request.user,
            )
            messages.success(request, f"Unlinked {ticket}.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)



# --------------------------------------------------
# Problem Close / Reopen
# --------------------------------------------------

class ProblemCloseView(
    ProblemChangePermissionMixin,
    View
):
    """
    Close a resolved problem.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        try:
            ProblemService.close_problem(problem, user=request.user)
            messages.success(request, "Problem closed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)


class ProblemReopenView(
    ProblemChangePermissionMixin,
    View
):
    """
    Reopen a closed problem.

    Requires:
        service_desk.change_problem
    """

    def post(self, request, pk):

        problem = get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

        try:
            ProblemService.reopen_problem(problem, user=request.user)
            messages.success(request, "Problem reopened.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:problem_detail", pk=problem.pk)

