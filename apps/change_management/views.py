from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.change_management.models import CABMeeting, ChangeRequest
from apps.change_management.serializers import (
    CABMeetingSerializer,
    ChangeCreateSerializer,
    ChangeDecisionSerializer,
    ChangeRequestSerializer,
    ChangeTicketSerializer,
)
from apps.change_management.services import ChangeService
from apps.service_desk.models import Ticket
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company, require_company

User = get_user_model()


@login_required
def change_list(request):
    company = get_active_company(request)
    qs = ChangeService.open_changes(company=company).select_related("change_request")
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/changes/list.html",
        {"title": "Changes", "page": page, "changes": page.object_list},
    )


@login_required
def change_detail(request, pk: int):
    ticket = get_object_or_404(
        TicketService.base_queryset().filter(ticket_type=Ticket.TicketType.CHANGE),
        pk=pk,
    )
    change = getattr(ticket, "change_request", None)
    return render(
        request,
        "itil/changes/detail.html",
        {
            "title": ticket.ticket_number,
            "ticket": ticket,
            "change": change,
            "approvals": change.approvals.select_related("approver").all() if change else [],
            "agents": User.objects.filter(is_staff=True, is_active=True),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def change_create(request):
    company = require_company(request)
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if title:
            ticket = ChangeService.create_change(
                title=title,
                description=request.POST.get("description") or "",
                company=company,
                change_type=request.POST.get("change_type") or ChangeRequest.ChangeType.NORMAL,
                risk=request.POST.get("risk") or ChangeRequest.Risk.MEDIUM,
                justification=request.POST.get("justification") or "",
                implementation_plan=request.POST.get("implementation_plan") or "",
                rollback_plan=request.POST.get("rollback_plan") or "",
                test_plan=request.POST.get("test_plan") or "",
                requester_user=request.user,
                actor=request.user,
            )
            messages.success(request, f"Change {ticket.ticket_number} created.")
            return redirect("changes:detail", pk=ticket.pk)
        messages.error(request, "Title is required.")
    return render(
        request,
        "itil/changes/create.html",
        {
            "title": "Create change",
            "change_types": ChangeRequest.ChangeType.choices,
            "risks": ChangeRequest.Risk.choices,
        },
    )


@login_required
@require_POST
def change_submit(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
    ChangeService.submit(ticket, actor=request.user)
    messages.success(request, "Change submitted.")
    return redirect("changes:detail", pk=pk)


@login_required
@require_POST
def change_request_approval(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
    approver = get_object_or_404(User, pk=request.POST.get("approver"))
    ChangeService.request_cab_approval(
        ticket,
        approver=approver,
        requested_by=request.user,
        reason=request.POST.get("reason") or "",
    )
    messages.success(request, "CAB approval requested.")
    return redirect("changes:detail", pk=pk)


@login_required
@require_POST
def change_decide(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
    approved = request.POST.get("approved") == "1"
    ChangeService.decide(
        ticket,
        approver=request.user,
        approved=approved,
        comment=request.POST.get("comment") or "",
    )
    messages.success(request, "Decision recorded.")
    return redirect("changes:detail", pk=pk)


@login_required
def cab_list(request):
    company = get_active_company(request)
    qs = CABMeeting.objects.all()
    if company:
        qs = qs.filter(company=company)
    page = Paginator(qs.order_by("-scheduled_at"), 20).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/changes/cab_list.html",
        {"title": "CAB meetings", "page": page},
    )


class ChangeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        company = get_active_company(request)
        qs = ChangeService.open_changes(company=company)
        return Response(ChangeTicketSerializer(qs, many=True).data)

    def create(self, request):
        ser = ChangeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ser.validated_data
        ticket = ChangeService.create_change(
            title=data["title"],
            description=data.get("description") or "",
            company=company,
            change_type=data.get("change_type"),
            risk=data.get("risk"),
            justification=data.get("justification") or "",
            implementation_plan=data.get("implementation_plan") or "",
            rollback_plan=data.get("rollback_plan") or "",
            test_plan=data.get("test_plan") or "",
            scheduled_start=data.get("scheduled_start"),
            scheduled_end=data.get("scheduled_end"),
            requester_user=request.user,
            actor=request.user,
        )
        return Response(
            ChangeRequestSerializer(ticket.change_request).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
        return Response(ChangeRequestSerializer(ticket.change_request).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
        change = ChangeService.submit(ticket, actor=request.user)
        return Response(ChangeRequestSerializer(change).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
        ser = ChangeDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ChangeService.decide(
            ticket,
            approver=request.user,
            approved=ser.validated_data["approved"],
            comment=ser.validated_data.get("comment") or "",
        )
        return Response(ChangeRequestSerializer(ticket.change_request).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.CHANGE)
        success = request.data.get("success", True)
        if isinstance(success, str):
            success = success.lower() in {"1", "true", "yes"}
        change = ChangeService.complete(ticket, success=bool(success), actor=request.user)
        return Response(ChangeRequestSerializer(change).data)


class CABMeetingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CABMeetingSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = CABMeeting.objects.prefetch_related("members", "changes").all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = get_active_company(self.request)
        serializer.save(company=company)