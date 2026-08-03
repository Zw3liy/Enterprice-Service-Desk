"""
Enterprise Service Desk
Service Desk Views

Handles:
- Dashboard
- Ticket management
- Ticket updates
- Ticket deletion
- Knowledge base
- Assets
- Notifications
- API dashboard

"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.views.generic import TemplateView


from .forms import TicketUpdateForm
from .models import Ticket


# ==========================================================
# Dashboard
# ==========================================================

class DashboardView(TemplateView):
    """
    Main Service Desk dashboard.
    """

    template_name = "service_desk/dashboard.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["ticket_count"] = Ticket.objects.count()

        context["recent_tickets"] = (
            Ticket.objects
            .order_by("-id")[:10]
        )

        return context



# ==========================================================
# Ticket List
# ==========================================================

@login_required
def ticket_list(request):
    """
    Display all tickets.
    """

    tickets = (
        Ticket.objects
        .all()
        .order_by("-id")
    )

    return render(
        request,
        "service_desk/ticket_list.html",
        {
            "tickets": tickets
        }
    )



# ==========================================================
# Ticket Detail
# ==========================================================

@login_required
def ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk
    )

    return render(
        request,
        "service_desk/ticket_detail.html",
        {
            "ticket": ticket
        }
    )



# ==========================================================
# Ticket Update
# ==========================================================

@login_required
def ticket_update(request, pk):
    """
    Update an existing ticket.
    """

    ticket = get_object_or_404(
        Ticket,
        pk=pk
    )


    if request.method == "POST":

        form = TicketUpdateForm(
            request.POST,
            request.FILES,
            instance=ticket
        )


        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Ticket updated successfully."
            )

            return redirect(
                "service_desk:ticket_detail",
                pk=ticket.pk
            )


    else:

        form = TicketUpdateForm(
            instance=ticket
        )


    return render(
        request,
        "service_desk/ticket_form.html",
        {
            "title": "Update Ticket",
            "form": form,
            "ticket": ticket
        }
    )



# ==========================================================
# Ticket Delete
# ==========================================================

@login_required
def ticket_delete(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk
    )


    if request.method == "POST":

        ticket.delete()

        messages.success(
            request,
            "Ticket deleted successfully."
        )

        return redirect(
            "service_desk:ticket_list"
        )


    return render(
        request,
        "service_desk/ticket_confirm_delete.html",
        {
            "ticket": ticket
        }
    )



# ==========================================================
# Knowledge Base
# ==========================================================

@login_required
def knowledge_list(request):

    return render(
        request,
        "service_desk/knowledge_list.html"
    )



@login_required
def knowledge_create(request):

    return render(
        request,
        "service_desk/knowledge_form.html"
    )



@login_required
def knowledge_detail(request, slug):

    return render(
        request,
        "service_desk/knowledge_detail.html",
        {
            "slug": slug
        }
    )



@login_required
def knowledge_feedback(request, slug):

    return redirect(
        "service_desk:knowledge_detail",
        slug=slug
    )



# ==========================================================
# Assets
# ==========================================================

@login_required
def asset_list(request):

    return render(
        request,
        "service_desk/asset_list.html"
    )


@login_required
def asset_create(request):

    return render(
        request,
        "service_desk/asset_form.html"
    )


@login_required
def asset_detail(request, pk):

    return render(
        request,
        "service_desk/asset_detail.html",
        {
            "pk": pk
        }
    )



# ==========================================================
# Reports
# ==========================================================

@login_required
def reports_index(request):

    return render(
        request,
        "service_desk/reports.html"
    )



# ==========================================================
# Notifications
# ==========================================================

@login_required
def notification_list(request):

    return render(
        request,
        "service_desk/notifications.html"
    )


@login_required
def notification_read(request, pk):

    return redirect(
        "service_desk:notifications"
    )



# ==========================================================
# Ticket API Dashboard
# ==========================================================

@login_required
def api_dashboard_json(request):

    data = {

        "tickets": Ticket.objects.count(),

        "open_tickets":
            Ticket.objects
            .filter(status="OPEN")
            .count(),

    }


    return JsonResponse(data)



# ==========================================================
# Compatibility aliases
# ==========================================================

# Older tests/modules may still reference these names

update_ticket = ticket_update

delete_ticket = ticket_delete