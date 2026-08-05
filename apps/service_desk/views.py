"""
apps/service_desk/views.py

Enterprise Service Desk
Phase 2.2.4 — Authorization Hardening

Responsibilities:
- Authentication enforcement
- RBAC permission enforcement
- Object-level ticket visibility
- Ticket ownership assignment
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

    template_name = "dashboard.html"

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