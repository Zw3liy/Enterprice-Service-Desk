from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import TicketCreateForm


def dashboard(request):
    context = {
        "title": "Enterprise Service Desk",
        "total_tickets": 0,
        "open_tickets": 0,
        "resolved_tickets": 0,
    }

    return render(
        request,
        "service_desk/dashboard.html",
        context
    )


def ticket_create(request):
    """Render and process the "New Support Ticket" form."""

    user = request.user if request.user.is_authenticated else None

    if request.method == "POST":
        form = TicketCreateForm(
            request.POST,
            request.FILES,
            user=user,
        )

        if form.is_valid():
            ticket = form.save()

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} was created successfully.",
            )

            return redirect("ticket_create")
    else:
        form = TicketCreateForm(user=user)

    context = {
        "title": "New Support Ticket",
        "form": form,
    }

    return render(
        request,
        "tickets/create.html",
        context,
    )
