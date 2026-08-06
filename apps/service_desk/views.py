from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from .models import Ticket


class IncidentDashboardView(PermissionRequiredMixin, TemplateView):
    template_name = "service_desk/incidents.html"

    permission_required = "service_desk.view_ticket"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        incidents = (
            Ticket.objects
            .select_related(
                "department",
                "assigned_to",
            )
            .order_by("-created_at")
        )

        context.update({

            "incidents": incidents,

            "total_incidents":
                incidents.count(),

            "pending_incidents":
                incidents.filter(
                    status__in=[
                        "OPEN",
                        "IN_PROGRESS",
                        "UNASSIGNED",
                    ]
                ),

            "resolved_incidents":
                incidents.filter(
                    status__in=[
                        "RESOLVED",
                        "CLOSED",
                    ]
                ),

            "critical_incidents":
                incidents.filter(
                    priority__in=[
                        "HIGH",
                        "CRITICAL",
                    ]
                ),

        })

        return context