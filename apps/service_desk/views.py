"""
apps/service_desk/views.py

Enterprise Service Desk
Phase 2.2.4 — Authorization Hardening
"""


from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    DetailView,
    UpdateView,
)

from .models import (
    Action,
    Approval,
    FishboneFactor,
    Notification,
    Problem,
    RootCauseAnalysis,
    SLAPolicy,
    Supplier,
    Ticket,
    TicketAttachment,
    TicketHistory,
)
from .forms.ticket_forms import TicketCreateForm
from .forms.problem_forms import ProblemCreateForm
from .forms.supplier_forms import SupplierCreateForm, SupplierUpdateForm
from .forms.sla_forms import SLAPolicyForm
from .forms.rca_forms import (
    ActionForm,
    ApprovalDecisionForm,
    ApprovalRequestForm,
    EvidenceForm,
    FishboneFactorForm,
    FiveWhysStepForm,
    RCADetailsForm,
)

from .security.policies import (
    get_problem_queryset,
    get_supplier_queryset,
    get_ticket_queryset,
)
from .security.mixins import (
    ServiceDeskLoginRequiredMixin,
    TicketPermissionMixin,
    TicketChangePermissionMixin,
    TicketViewPermissionMixin,
    ProblemPermissionMixin,
    ProblemViewPermissionMixin,
    ProblemCreatePermissionMixin,
    ProblemChangePermissionMixin,
    SupplierChangePermissionMixin,
    SupplierCreatePermissionMixin,
    SupplierViewPermissionMixin,
    SLAPolicyViewPermissionMixin,
    SLAPolicyChangePermissionMixin,
)
from .selectors.ticket_selector import TicketSelector
from .selectors.problem_selector import ProblemSelector
from .selectors.supplier_selector import SupplierSelector
from .selectors.sla_selector import SLASelector
from .selectors.notification_selector import NotificationSelector
from .services.ticket_service import TicketService
from .services.problem_service import ProblemService
from .services.supplier_service import SupplierService
from .services.sla_service import SLAService
from .services.notification_service import NotificationService

User = get_user_model()



# --------------------------------------------------
# Dashboard
# --------------------------------------------------

class DashboardView(
    TicketPermissionMixin,
    TemplateView
):
    """
    Main enterprise dashboard.

    Every number and every row rendered here is derived from the
    RBAC-scoped queryset returned by
    ``security.policies.get_ticket_queryset`` — the dashboard never
    reads ``Ticket.objects`` directly, so a Requester can never see
    another user's counts and a Manager can never see another
    department's counts.
    """

    template_name = "service_desk/dashboard.html"

    permission_required = (
        "service_desk.view_ticket"
    )

    RECENT_TICKET_LIMIT = 10

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        tickets = get_ticket_queryset(self.request.user)

        # Single aggregate query for every status bucket, so the
        # dashboard costs one round trip rather than one per card.
        counts = tickets.aggregate(
            total=Count("pk"),
            open=Count("pk", filter=Q(status="open")),
            in_progress=Count("pk", filter=Q(status="in_progress")),
            pending=Count("pk", filter=Q(status="pending")),
            resolved=Count("pk", filter=Q(status="resolved")),
            awaiting_confirmation=Count(
                "pk", filter=Q(status="awaiting_confirmation")
            ),
            closed=Count("pk", filter=Q(status="closed")),
            unassigned=Count("pk", filter=Q(assigned_to__isnull=True)),
            high_priority=Count(
                "pk", filter=Q(priority__in=["high", "urgent"])
            ),
        )

        context.update(
            {
                "total_tickets": counts["total"],
                "open_tickets": counts["open"],
                "in_progress_tickets": counts["in_progress"],
                "pending_tickets": counts["pending"],
                "resolved_tickets": counts["resolved"],
                "awaiting_confirmation_tickets": counts[
                    "awaiting_confirmation"
                ],
                "closed_tickets": counts["closed"],
                "unassigned_tickets": counts["unassigned"],
                "high_priority_tickets": counts["high_priority"],
                "active_tickets": (
                    counts["open"]
                    + counts["in_progress"]
                    + counts["pending"]
                ),
                "recent_tickets": tickets.select_related(
                    "department",
                    "assigned_to",
                    "created_by",
                ).order_by("-created_at")[: self.RECENT_TICKET_LIMIT],
            }
        )

        # Problem visibility is a separate policy (ADR-010): Requesters
        # get nothing, so the Problem card simply renders zero for them.
        problems = get_problem_queryset(self.request.user)

        context["problem_total"] = problems.count()
        context["problem_open"] = problems.exclude(
            status__in=["resolved", "closed"]
        ).count()
        context["known_errors"] = problems.filter(
            is_known_error=True
        ).count()
        context["can_view_problems"] = self.request.user.has_perm(
            "service_desk.view_problem"
        )

        # SLA indicators, scoped through exactly the same ticket
        # queryset as every other number on this page.
        sla_summary = SLASelector.dashboard_summary(tickets)

        context["sla_summary"] = sla_summary
        context["sla_breached"] = sla_summary["breached"]
        context["sla_at_risk"] = sla_summary["at_risk"]

        context["unread_notifications"] = (
            NotificationSelector.unread_count(self.request.user)
        )
        context["recent_notifications"] = NotificationSelector.recent(
            self.request.user, limit=5
        )

        return context



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

    Ownership, assignment and status cannot be supplied by the client —
    only the declared form fields reach TicketService.create_ticket.
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


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        context["no_active_request_types"] = bool(
            getattr(form, "no_active_request_types", False)
        )
        context["no_departments"] = bool(
            getattr(form, "no_departments", False)
        )
        return context


    def form_valid(self, form):
        # Never accept client-supplied ownership or lifecycle fields.
        payload = {
            key: form.cleaned_data[key]
            for key in (
                "title",
                "description",
                "priority",
                "urgency",
                "department",
                "request_type",
                "tags",
            )
            if key in form.cleaned_data
        }

        attachment = form.cleaned_data.get("attachment")
        if attachment is not None:
            payload["attachment"] = attachment

        try:
            self.object = TicketService.create_ticket(
                created_by=self.request.user,
                **payload,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Ticket #{self.object.pk} created successfully.",
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
        # change_ticket) — ADR-010, Decision 3.
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

    Any role that can see a ticket can comment on it — there is
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
# Ticket Work Note (internal — Technician/Manager only)
# --------------------------------------------------

class TicketWorkNoteView(
    TicketChangePermissionMixin,
    View
):
    """
    Add an internal work note to a ticket.

    Requires:
        service_desk.change_ticket

    Work notes are never visible to Requesters — the template
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
    TicketViewPermissionMixin (view_ticket — which Requesters
    hold) because the real gate is "are you the requester,"
    enforced in the service layer (change_status rejects
    non-requesters for the awaiting_confirmation → closed
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
    separate Incident model) — visibility is scoped through
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
            none — Requesters cannot access Problem records
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

        context["stats"] = ProblemSelector.dashboard_statistics(
            self.get_queryset()
        )

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

    Supports an active/inactive filter and a free-text search, both
    applied *after* the RBAC scoping so neither can widen visibility.
    """

    model = Supplier
    template_name = "suppliers/list.html"
    context_object_name = "suppliers"
    paginate_by = 25
    permission_required = (
        "service_desk.view_supplier",
    )


    def get_queryset(self):

        queryset = get_supplier_queryset(
            self.request.user
        ).select_related("department")

        status = self.request.GET.get("status", "").strip()

        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        search = self.request.GET.get("q", "").strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(contact_name__icontains=search)
                | Q(contact_email__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset.order_by("name")


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["stats"] = SupplierSelector.scoped_summary(
            get_supplier_queryset(self.request.user)
        )
        context["active_status"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")

        return context


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


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


    def form_valid(self, form):

        try:
            self.object = SupplierService.create_supplier(
                user=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Supplier '{self.object.name}' created.",
        )

        return redirect(
            "service_desk:supplier_detail",
            pk=self.object.pk,
        )


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
        return get_supplier_queryset(
            self.request.user
        ).select_related("department")


# --------------------------------------------------
# Supplier Update


class SupplierUpdateView(
    SupplierChangePermissionMixin,
    UpdateView
):
    """
    Supplier update.

    Requires:
        service_desk.change_supplier

    The object is fetched through the RBAC-scoped queryset, so a
    Manager cannot reach another department's supplier by guessing
    a primary key.
    """

    model = Supplier
    form_class = SupplierUpdateForm
    template_name = "suppliers/update.html"
    context_object_name = "supplier"
    permission_required = (
        "service_desk.change_supplier",
    )


    def get_queryset(self):
        return get_supplier_queryset(self.request.user)


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


    def form_valid(self, form):

        # ModelForm validation has already written the submitted values
        # onto form.instance (which *is* self.object), so passing that
        # instance to the service would make its change-detection see
        # "nothing changed" and skip the save. Re-read the persisted row
        # so the service compares against real stored state.
        persisted = Supplier.objects.get(pk=self.object.pk)

        try:
            self.object = SupplierService.update_supplier(
                persisted,
                user=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Supplier updated.")

        return redirect(
            "service_desk:supplier_detail",
            pk=self.object.pk,
        )


# --------------------------------------------------
# Supplier Lifecycle


class SupplierDeactivateView(
    SupplierChangePermissionMixin,
    View
):
    """
    Retire a supplier (active -> inactive).

    Suppliers are never hard-deleted through the UI: existing
    tickets, contracts and audit records reference them.
    """

    def post(self, request, pk):

        supplier = get_object_or_404(
            get_supplier_queryset(request.user),
            pk=pk,
        )

        try:
            SupplierService.deactivate_supplier(
                supplier,
                user=request.user,
            )
            messages.success(
                request,
                f"Supplier '{supplier.name}' deactivated.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:supplier_detail", pk=supplier.pk)


class SupplierActivateView(
    SupplierChangePermissionMixin,
    View
):
    """
    Reinstate a retired supplier (inactive -> active).
    """

    def post(self, request, pk):

        supplier = get_object_or_404(
            get_supplier_queryset(request.user),
            pk=pk,
        )

        try:
            SupplierService.activate_supplier(
                supplier,
                user=request.user,
            )
            messages.success(
                request,
                f"Supplier '{supplier.name}' reactivated.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:supplier_detail", pk=supplier.pk)


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

        # --- RCA authoring surface ---------------------------------
        rca = context["rca"]

        can_edit = self.request.user.has_perm(
            "service_desk.change_problem"
        )

        rca_locked = bool(
            rca and rca.status in ProblemService.CLOSED_RCA_STATUSES
        )

        context["rca_locked"] = rca_locked
        context["can_edit_rca"] = can_edit and not rca_locked

        if rca:
            context["five_whys"] = rca.five_whys.all()
            context["fishbone_factors"] = rca.fishbone_factors.all()
            context["evidence_items"] = rca.evidence.all()
            context["actions"] = rca.actions.select_related("assigned_to")
            context["approvals"] = rca.approvals.select_related("approver")
            context["pending_approval"] = rca.approvals.filter(
                approver=self.request.user,
                status="pending",
            ).first()
        else:
            context["five_whys"] = []
            context["fishbone_factors"] = []
            context["evidence_items"] = []
            context["actions"] = []
            context["approvals"] = []
            context["pending_approval"] = None

        if context["can_edit_rca"]:
            context["rca_form"] = RCADetailsForm(instance=rca)
            context["five_whys_form"] = FiveWhysStepForm()
            context["fishbone_form"] = FishboneFactorForm()
            context["evidence_form"] = EvidenceForm()
            context["action_form"] = ActionForm()
            context["approval_request_form"] = ApprovalRequestForm()

        if context["pending_approval"]:
            context["approval_decision_form"] = ApprovalDecisionForm()

        context["action_status_flow"] = ProblemService.ACTION_STATUS_FLOW

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
    populated — enforced by ProblemService.mark_known_error.
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
    Administrator only despite the "view" permission name —
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


# --------------------------------------------------
# SLA Management
# --------------------------------------------------

class SLADashboardView(
    TicketViewPermissionMixin,
    TemplateView
):
    """
    Operational SLA view.

    Every clock shown here belongs to a ticket in
    get_ticket_queryset(request.user), so a Requester sees the SLA
    state of their own tickets and nothing else, and a Manager sees
    only their departments'.
    """

    template_name = "sla/dashboard.html"

    permission_required = (
        "service_desk.view_ticket"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        tickets = get_ticket_queryset(self.request.user)

        context["summary"] = SLASelector.dashboard_summary(tickets)
        context["breached"] = SLASelector.breached(tickets)[:50]
        context["at_risk"] = SLASelector.at_risk(tickets)[:50]
        context["escalations"] = SLASelector.escalations(tickets)
        context["can_manage_policies"] = self.request.user.has_perm(
            "service_desk.view_slapolicy"
        )

        if context["can_manage_policies"]:
            from .models import SLARunLog

            context["recent_sla_runs"] = SLARunLog.objects.all()[:10]

        return context


class SLAPolicyListView(
    SLAPolicyViewPermissionMixin,
    ListView
):
    """
    SLA policy catalogue, scoped by SLASelector.policies_for_user.
    """

    model = SLAPolicy

    template_name = "sla/policy_list.html"

    context_object_name = "policies"

    permission_required = (
        "service_desk.view_slapolicy"
    )

    def get_queryset(self):
        return SLASelector.policies_for_user(self.request.user)


class SLAPolicyCreateView(
    SLAPolicyChangePermissionMixin,
    CreateView
):
    """
    Create an SLA policy.

    Requires:
        service_desk.add_slapolicy
    """

    model = SLAPolicy

    form_class = SLAPolicyForm

    template_name = "sla/policy_form.html"

    permission_required = (
        "service_desk.add_slapolicy"
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):

        try:
            SLAService.assert_policy_scope_allowed(
                self.request.user,
                form.cleaned_data.get("department"),
            )
            self.object = SLAService.create_policy(**form.cleaned_data)
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "SLA policy created.")

        return redirect("service_desk:sla_policy_list")


class SLAPolicyUpdateView(
    SLAPolicyChangePermissionMixin,
    UpdateView
):
    """
    Update an SLA policy.

    Editing a policy never retroactively moves the deadlines of
    tickets already under way — TicketSLA freezes its own dates at
    attach time (see models/sla.py).
    """

    model = SLAPolicy

    form_class = SLAPolicyForm

    template_name = "sla/policy_form.html"

    context_object_name = "policy"

    permission_required = (
        "service_desk.change_slapolicy"
    )

    def get_queryset(self):
        return SLASelector.policies_for_user(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):

        persisted = SLAPolicy.objects.get(pk=self.object.pk)

        try:
            SLAService.assert_policy_scope_allowed(
                self.request.user,
                form.cleaned_data.get("department"),
            )
            self.object = SLAService.update_policy(
                persisted,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "SLA policy updated.")

        return redirect("service_desk:sla_policy_list")


# --------------------------------------------------
# Notifications
# --------------------------------------------------

class NotificationListView(
    ServiceDeskLoginRequiredMixin,
    ListView
):
    """
    The signed-in user's own notification inbox.

    Deliberately guarded by authentication only, not a model
    permission: a notification belongs to its recipient, and the
    queryset is keyed on request.user, so there is nothing here a
    Requester should be barred from seeing about their own tickets.
    """

    model = Notification

    template_name = "notifications/list.html"

    context_object_name = "notifications"

    paginate_by = 25

    def get_queryset(self):
        return NotificationSelector.for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_count"] = NotificationSelector.unread_count(
            self.request.user
        )
        return context


class NotificationReadView(
    ServiceDeskLoginRequiredMixin,
    View
):
    """
    Mark one notification read and follow it to its target.
    """

    def post(self, request, pk):

        notification = get_object_or_404(
            NotificationSelector.for_user(request.user),
            pk=pk,
        )

        NotificationService.mark_read(notification, request.user)

        return redirect(notification.target_url())


class NotificationReadAllView(
    ServiceDeskLoginRequiredMixin,
    View
):
    """
    Mark every unread notification read.
    """

    def post(self, request):

        count = NotificationService.mark_all_read(request.user)

        messages.success(
            request,
            f"{count} notification(s) marked as read.",
        )

        return redirect("service_desk:notification_list")


# --------------------------------------------------
# Problem RCA workflows
#
# FiveWhys, FishboneFactor, Evidence, Action and Approval were
# rendered read-only on the Problem detail page with no way to create
# one outside the Django admin. Each view below is a thin POST handler
# that validates shape with a form and then delegates every mutation
# to ProblemService — no view here writes to a model directly.
# --------------------------------------------------

class ProblemRCAActionMixin(
    ProblemChangePermissionMixin,
    View
):
    """
    Shared plumbing for the RCA action views.

    Resolves the problem through get_problem_queryset, so an
    out-of-scope problem is a 404 for everybody — including a
    Requester, who has no Problem visibility at all (ADR-010).
    """

    def get_problem(self, request, pk):
        return get_object_or_404(
            get_problem_queryset(request.user),
            pk=pk,
        )

    def back(self, problem):
        return redirect("service_desk:problem_detail", pk=problem.pk)

    def report_form_errors(self, request, form):
        for field, errors in form.errors.items():
            label = "" if field == "__all__" else f"{field}: "
            for error in errors:
                messages.error(request, f"{label}{error}")


class ProblemRCAUpdateView(ProblemRCAActionMixin):
    """
    Edit the RCA narrative (method, statement, mitigation, ...).
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)
        rca = ProblemService.get_or_create_rca(problem, user=request.user)

        form = RCADetailsForm(request.POST, instance=rca)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.update_rca(
                RootCauseAnalysis.objects.get(pk=rca.pk),
                user=request.user,
                **form.cleaned_data,
            )
            messages.success(request, "Root Cause Analysis updated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemFiveWhysAddView(ProblemRCAActionMixin):
    """
    Append a step to the Five Whys chain.
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)

        form = FiveWhysStepForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.add_five_whys_step(
                problem,
                question=form.cleaned_data["question"],
                answer=form.cleaned_data["answer"],
                user=request.user,
            )
            messages.success(request, "Five Whys step added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemFishboneAddView(ProblemRCAActionMixin):
    """
    Record a contributing factor on the Ishikawa diagram.
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)

        form = FishboneFactorForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.add_fishbone_factor(
                problem,
                category=form.cleaned_data["category"],
                factor_description=form.cleaned_data["factor_description"],
                is_root_cause=form.cleaned_data.get("is_root_cause", False),
                user=request.user,
            )
            messages.success(request, "Contributing factor added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemFishboneRootCauseView(ProblemRCAActionMixin):
    """
    Flag (or unflag) a factor as the identified root cause.
    """

    def post(self, request, pk, factor_pk):

        problem = self.get_problem(request, pk)

        factor = get_object_or_404(
            FishboneFactor,
            pk=factor_pk,
            rca__problem=problem,
        )

        try:
            ProblemService.set_factor_as_root_cause(
                factor,
                user=request.user,
                is_root_cause=not factor.is_root_cause,
            )
            messages.success(request, "Factor updated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemEvidenceAddView(ProblemRCAActionMixin):
    """
    Attach supporting evidence to the investigation.
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)

        form = EvidenceForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.add_evidence(
                problem,
                title=form.cleaned_data["title"],
                file_or_link=form.cleaned_data["file_or_link"],
                description=form.cleaned_data.get("description", ""),
                user=request.user,
            )
            messages.success(request, "Evidence recorded.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemActionAddView(ProblemRCAActionMixin):
    """
    Raise a corrective or preventive action (CAPA).
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)

        form = ActionForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.add_action(
                problem,
                action_type=form.cleaned_data["action_type"],
                description=form.cleaned_data["description"],
                due_date=form.cleaned_data["due_date"],
                assigned_to=form.cleaned_data.get("assigned_to"),
                user=request.user,
            )
            messages.success(request, "Action raised.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemActionStatusView(ProblemRCAActionMixin):
    """
    Advance a CAPA through its lifecycle.
    """

    def post(self, request, pk, action_pk):

        problem = self.get_problem(request, pk)

        action = get_object_or_404(
            Action,
            pk=action_pk,
            rca__problem=problem,
        )

        try:
            ProblemService.change_action_status(
                action,
                request.POST.get("status", ""),
                user=request.user,
            )
            messages.success(request, "Action updated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemApprovalRequestView(ProblemRCAActionMixin):
    """
    Ask a named reviewer to sign the RCA off.
    """

    def post(self, request, pk):

        problem = self.get_problem(request, pk)

        form = ApprovalRequestForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.request_approval(
                problem,
                approver=form.cleaned_data["approver"],
                user=request.user,
            )
            messages.success(request, "Sign-off requested.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)


class ProblemApprovalDecisionView(ProblemRCAActionMixin):
    """
    Record the nominated approver's decision.

    The "only the nominated approver may decide, and only once" rule
    is enforced in ProblemService.decide_approval, not here.
    """

    def post(self, request, pk, approval_pk):

        problem = self.get_problem(request, pk)

        approval = get_object_or_404(
            Approval,
            pk=approval_pk,
            rca__problem=problem,
        )

        form = ApprovalDecisionForm(request.POST)

        if not form.is_valid():
            self.report_form_errors(request, form)
            return self.back(problem)

        try:
            ProblemService.decide_approval(
                approval,
                status=form.cleaned_data["status"],
                comments=form.cleaned_data.get("comments", ""),
                user=request.user,
            )
            messages.success(request, "Decision recorded.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return self.back(problem)
