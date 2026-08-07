"""
apps/service_desk/views.py

Enterprise Service Desk
Phase 2.2.4 — Authorization Hardening
"""


from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    DetailView,
)

from .models import Ticket
from .forms.ticket_forms import TicketCreateForm

from .security.policies import get_ticket_queryset
from .security.mixins import (
    TicketPermissionMixin,
    TicketChangePermissionMixin,
    TicketViewPermissionMixin,
)
from .selectors.ticket_selector import TicketSelector
from .services.ticket_service import TicketService

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

        context["history"] = self.object.history.select_related(
            "performed_by"
        ).order_by("-created_at")

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
# Ticket Close / Reopen
# --------------------------------------------------

class TicketCloseView(
    TicketChangePermissionMixin,
    View
):
    """
    Close a resolved ticket.

    Requires:
        service_desk.change_ticket
    """

    def post(self, request, pk):

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=pk,
        )

        try:
            TicketService.close_ticket(ticket, user=request.user)
            messages.success(request, "Ticket closed.")
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
