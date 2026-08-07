"""
apps/service_desk/views.py

Enterprise Service Desk
Phase 2.2.4 — Authorization Hardening
"""


from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    DetailView,
)

from .models import Ticket
from .forms.ticket_forms import TicketCreateForm

from .security.policies import get_ticket_queryset
from .security.mixins import TicketPermissionMixin
from .selectors.ticket_selector import TicketSelector



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

        form.instance.created_by = (
            self.request.user
        )

        return super().form_valid(form)



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
