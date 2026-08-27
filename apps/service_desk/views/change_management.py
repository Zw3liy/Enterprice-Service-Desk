from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.service_desk.models import ChangeRequest, CABDecision, ChangeTask
from apps.service_desk.security.policies import (
    get_ticket_queryset,
    is_administrator,
    is_manager,
)
from apps.service_desk.selectors.change_management import get_change_requests
from apps.service_desk.services.change_management import (
    approve_change,
    cancel_change,
    close_change,
    implement_change,
    reject_change,
    schedule_change,
    submit_change,
)


def _can_manage(user):
    return is_administrator(user) or is_manager(user)


@login_required
def change_list(request):
    if not _can_manage(request.user):
        return HttpResponseForbidden("Change Management access denied.")

    changes = get_change_requests(request.user)

    return render(
        request,
        "service_desk/change_management/list.html",
        {"changes": changes},
    )


@login_required
def change_detail(request, pk):
    if not _can_manage(request.user):
        return HttpResponseForbidden("Change Management access denied.")

    change = get_object_or_404(
        get_change_requests(request.user),
        pk=pk,
    )

    return render(
        request,
        "service_desk/change_management/detail.html",
        {"change": change},
    )


@login_required
def change_create(request):
    if not _can_manage(request.user):
        return HttpResponseForbidden("Change Management access denied.")

    if request.method == "POST":
        ticket_id = request.POST.get("ticket")
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        risk = request.POST.get("risk", ChangeRequest.Risk.MEDIUM)

        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=ticket_id,
        )

        change = ChangeRequest.objects.create(
            ticket=ticket,
            title=title,
            description=description,
            risk=risk,
            requester=request.user,
        )

        return redirect("change-management:detail", pk=change.pk)

    tickets = get_ticket_queryset(request.user)

    return render(
        request,
        "service_desk/change_management/create.html",
        {"tickets": tickets},
    )


@login_required
def change_action(request, pk, action):
    if not _can_manage(request.user):
        return HttpResponseForbidden("Change Management access denied.")

    change = get_object_or_404(
        get_change_requests(request.user),
        pk=pk,
    )

    if request.method != "POST":
        return HttpResponseForbidden("Lifecycle actions require POST.")

    notes = request.POST.get("notes", "")

    actions = {
        "submit": lambda: submit_change(request.user, change),
        "approve": lambda: approve_change(request.user, change, notes),
        "reject": lambda: reject_change(request.user, change, notes),
        "schedule": lambda: schedule_change(request.user, change),
        "implement": lambda: implement_change(request.user, change),
        "close": lambda: close_change(request.user, change),
        "cancel": lambda: cancel_change(request.user, change),
    }

    if action not in actions:
        return HttpResponseForbidden("Unknown Change Management action.")

    actions[action]()

    return redirect("change-management:detail", pk=change.pk)