from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TicketForm, TicketUpdateForm
from .models import Ticket


@login_required
def dashboard(request):
    tickets = Ticket.objects.all()

    context = {
        "title": "Enterprise Service Desk",
        "total_tickets": tickets.count(),
        "open_tickets": tickets.filter(status="OPEN").count(),
        "resolved_tickets": tickets.filter(status="RESOLVED").count(),
        "recent_tickets": tickets.order_by("-created_at")[:10],
    }

    return render(
        request,
        "service_desk/dashboard.html",
        context,
    )


@login_required
def ticket_list(request):

    tickets = Ticket.objects.all()

    status = request.GET.get("status")
    if status:
        tickets = tickets.filter(status=status)

    priority = request.GET.get("priority")
    if priority:
        tickets = tickets.filter(priority=priority)

    category = request.GET.get("category")
    if category:
        tickets = tickets.filter(category=category)

    search = request.GET.get("search")
    if search:
        tickets = tickets.filter(subject__icontains=search)

    context = {
        "title": "Ticket List",
        "tickets": tickets.order_by("-created_at"),
        "status": status,
    }

    return render(
        request,
        "service_desk/ticket_list.html",
        context,
    )


@login_required
def ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    return render(
        request,
        "service_desk/ticket_detail.html",
        {
            "title": ticket.subject,
            "ticket": ticket,
        },
    )


@login_required
def ticket_create(request):

    if request.method == "POST":

        form = TicketForm(request.POST)

        if form.is_valid():

            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        form = TicketForm()

    return render(
        request,
        "service_desk/ticket_form.html",
        {
            "title": "Create Ticket",
            "form": form,
        },
    )


@login_required
def ticket_update(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        form = TicketUpdateForm(
            request.POST,
            instance=ticket,
        )

        if form.is_valid():

            form.save()

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        form = TicketUpdateForm(
            instance=ticket,
        )

    return render(
        request,
        "service_desk/ticket_form.html",
        {
            "title": "Update Ticket",
            "ticket": ticket,
            "form": form,
        },
    )


@login_required
def ticket_delete(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        ticket.delete()

        return redirect("ticket_list")

    return render(
        request,
        "service_desk/ticket_confirm_delete.html",
        {
            "title": "Delete Ticket",
            "ticket": ticket,
        },
    )