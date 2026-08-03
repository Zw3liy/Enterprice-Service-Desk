from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.problem_management.models import ProblemRecord
from apps.problem_management.serializers import (
    LinkIncidentSerializer,
    ProblemCreateSerializer,
    ProblemRecordSerializer,
    ProblemTicketSerializer,
    RootCauseSerializer,
)
from apps.problem_management.services import ProblemService
from apps.service_desk.models import Ticket
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company, require_company


@login_required
def problem_list(request):
    company = get_active_company(request)
    qs = ProblemService.open_problems(company=company)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/problems/list.html",
        {"title": "Problems", "page": page, "problems": page.object_list},
    )


@login_required
def problem_detail(request, pk: int):
    ticket = get_object_or_404(
        TicketService.base_queryset().filter(ticket_type=Ticket.TicketType.PROBLEM),
        pk=pk,
    )
    record = getattr(ticket, "problem_record", None)
    return render(
        request,
        "itil/problems/detail.html",
        {"title": ticket.ticket_number, "ticket": ticket, "record": record},
    )


@login_required
@require_http_methods(["GET", "POST"])
def problem_create(request):
    company = require_company(request)
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if title:
            ticket = ProblemService.create_problem(
                title=title,
                description=request.POST.get("description") or "",
                company=company,
                requester_user=request.user,
                actor=request.user,
            )
            messages.success(request, f"Problem {ticket.ticket_number} created.")
            return redirect("problems:detail", pk=ticket.pk)
        messages.error(request, "Title is required.")
    return render(request, "itil/problems/create.html", {"title": "Create problem"})


@login_required
@require_POST
def set_root_cause(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.PROBLEM)
    ProblemService.set_root_cause(
        ticket,
        root_cause=request.POST.get("root_cause") or "",
        workaround=request.POST.get("workaround") or "",
        actor=request.user,
    )
    messages.success(request, "Root cause recorded.")
    return redirect("problems:detail", pk=pk)


@login_required
@require_POST
def link_incident(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.PROBLEM)
    incident_id = request.POST.get("incident_id")
    incident = get_object_or_404(Ticket, pk=incident_id, ticket_type=Ticket.TicketType.INCIDENT)
    ProblemService.link_incident(ticket, incident)
    messages.success(request, f"Linked {incident.ticket_number}.")
    return redirect("problems:detail", pk=pk)


class ProblemViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        company = get_active_company(request)
        qs = ProblemService.open_problems(company=company)
        return Response(ProblemTicketSerializer(qs, many=True).data)

    def create(self, request):
        ser = ProblemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        ticket = ProblemService.create_problem(
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description") or "",
            company=company,
            requester_user=request.user,
            actor=request.user,
            auto_assign=ser.validated_data.get("auto_assign") or False,
        )
        record = ticket.problem_record
        return Response(
            ProblemRecordSerializer(record).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.PROBLEM)
        record = getattr(ticket, "problem_record", None)
        if record is None:
            record = ProblemRecord.objects.create(ticket=ticket, company=ticket.company)
        return Response(ProblemRecordSerializer(record).data)

    @action(detail=True, methods=["post"])
    def root_cause(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.PROBLEM)
        ser = RootCauseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        record = ProblemService.set_root_cause(
            ticket,
            root_cause=ser.validated_data["root_cause"],
            workaround=ser.validated_data.get("workaround") or "",
            actor=request.user,
        )
        return Response(ProblemRecordSerializer(record).data)

    @action(detail=True, methods=["post"])
    def link_incident(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.PROBLEM)
        ser = LinkIncidentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        incident = get_object_or_404(
            Ticket,
            pk=ser.validated_data["incident_id"],
            ticket_type=Ticket.TicketType.INCIDENT,
        )
        record = ProblemService.link_incident(ticket, incident)
        return Response(ProblemRecordSerializer(record).data)