"""Incident management UI + API views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.incident_management.models import MajorIncident
from apps.incident_management.serializers import (
    DeclareMajorSerializer,
    IncidentTimelineSerializer,
    IncidentTicketSerializer,
    MajorIncidentSerializer,
)
from apps.incident_management.services import IncidentService
from apps.service_desk.models import Ticket
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company, require_company

User = get_user_model()


@login_required
def incident_list(request):
    company = get_active_company(request)
    qs = IncidentService.open_incidents(company=company)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/incidents/list.html",
        {
            "title": "Incidents",
            "page": page,
            "incidents": page.object_list,
            "company": company,
        },
    )


@login_required
def incident_detail(request, pk: int):
    ticket = get_object_or_404(
        TicketService.base_queryset().filter(ticket_type=Ticket.TicketType.INCIDENT),
        pk=pk,
    )
    major = getattr(ticket, "major_incident_record", None)
    timeline = IncidentService.timeline(ticket)
    return render(
        request,
        "itil/incidents/detail.html",
        {
            "title": ticket.ticket_number,
            "ticket": ticket,
            "major": major,
            "timeline": timeline,
            "agents": User.objects.filter(is_staff=True, is_active=True),
        },
    )


@login_required
@require_POST
def declare_major(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, ticket_type=Ticket.TicketType.INCIDENT)
    commander_id = request.POST.get("commander")
    commander = User.objects.filter(pk=commander_id).first() if commander_id else None
    IncidentService.declare_major(
        ticket,
        severity=request.POST.get("severity") or MajorIncident.Severity.SEV1,
        commander=commander,
        customer_impact=request.POST.get("customer_impact") or "",
        bridge_channel=request.POST.get("bridge_channel") or "",
        actor=request.user,
    )
    messages.success(request, "Major incident declared.")
    return redirect("incidents:detail", pk=pk)


@login_required
@require_POST
def add_timeline(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk)
    message = (request.POST.get("message") or "").strip()
    if message:
        IncidentService.add_timeline(
            ticket,
            message=message,
            author=request.user,
            is_public=request.POST.get("is_public") == "on",
            event_type=request.POST.get("event_type") or "update",
        )
        messages.success(request, "Timeline updated.")
    return redirect("incidents:detail", pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def incident_create(request):
    company = require_company(request)
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = request.POST.get("description") or ""
        if title:
            ticket = IncidentService.create_incident(
                title=title,
                description=description,
                company=company,
                requester_user=request.user,
                actor=request.user,
                auto_assign=bool(request.POST.get("auto_assign")),
            )
            messages.success(request, f"Incident {ticket.ticket_number} created.")
            return redirect("incidents:detail", pk=ticket.pk)
        messages.error(request, "Title is required.")
    return render(
        request,
        "itil/incidents/create.html",
        {"title": "Create incident", "company": company},
    )


class IncidentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = IncidentTicketSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        return TicketService.search(
            company=company, ticket_type=Ticket.TicketType.INCIDENT
        )

    @action(detail=True, methods=["post"])
    def declare_major(self, request, pk=None):
        ticket = self.get_object()
        ser = DeclareMajorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        commander = None
        if ser.validated_data.get("commander"):
            commander = User.objects.filter(pk=ser.validated_data["commander"]).first()
        record = IncidentService.declare_major(
            ticket,
            severity=ser.validated_data["severity"],
            commander=commander,
            customer_impact=ser.validated_data.get("customer_impact") or "",
            bridge_channel=ser.validated_data.get("bridge_channel") or "",
            actor=request.user,
        )
        return Response(MajorIncidentSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def timeline(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            ser = IncidentTimelineSerializer(data={**request.data, "ticket": ticket.pk})
            ser.is_valid(raise_exception=True)
            event = IncidentService.add_timeline(
                ticket,
                message=ser.validated_data["message"],
                event_type=ser.validated_data.get("event_type") or "update",
                author=request.user,
                is_public=ser.validated_data.get("is_public") or False,
            )
            return Response(
                IncidentTimelineSerializer(event).data, status=status.HTTP_201_CREATED
            )
        events = IncidentService.timeline(ticket)
        return Response(IncidentTimelineSerializer(events, many=True).data)


class MajorIncidentListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        qs = MajorIncident.objects.select_related("ticket", "commander")
        if company:
            qs = qs.filter(company=company)
        return Response(MajorIncidentSerializer(qs, many=True).data)