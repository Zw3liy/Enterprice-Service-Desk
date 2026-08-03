from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customer_portal.models import PortalAnnouncement
from apps.customer_portal.serializers import (
    PortalAnnouncementSerializer,
    PortalCatalogSerializer,
    PortalKnowledgeSerializer,
    PortalProfileSerializer,
    PortalRequestCreateSerializer,
    PortalTicketDetailSerializer,
    PortalTicketSerializer,
)
from apps.customer_portal.services import PortalService
from apps.service_desk.models import RequestType, Ticket
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company, require_company


@login_required
def portal_home(request):
    company = require_company(request)
    profile = PortalService.ensure_profile(request.user, company)
    tickets = PortalService.my_tickets(request.user, company)[:10]
    catalog = PortalService.catalog(company)[:12]
    announcements = PortalService.announcements(company)[:5]
    articles = PortalService.knowledge(company)[:5]
    return render(
        request,
        "portal/home.html",
        {
            "title": "Service Portal",
            "profile": profile,
            "tickets": tickets,
            "catalog": catalog,
            "announcements": announcements,
            "articles": articles,
            "company": company,
        },
    )


@login_required
def portal_tickets(request):
    company = get_active_company(request)
    qs = PortalService.my_tickets(request.user, company)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "portal/tickets.html",
        {"title": "My requests", "page": page},
    )


@login_required
def portal_ticket_detail(request, pk: int):
    ticket = get_object_or_404(
        PortalService.my_tickets(request.user),
        pk=pk,
    )
    return render(
        request,
        "portal/ticket_detail.html",
        {
            "title": ticket.ticket_number,
            "ticket": ticket,
            "comments": ticket.comments.filter(is_internal=False).select_related("author"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def portal_new_request(request):
    company = require_company(request)
    catalog = PortalService.catalog(company)
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        rt_id = request.POST.get("request_type")
        rt = RequestType.objects.filter(pk=rt_id, department__company=company).first() if rt_id else None
        if title:
            ticket = PortalService.create_request(
                request.user,
                company,
                title=title,
                description=request.POST.get("description") or "",
                request_type=rt,
            )
            messages.success(request, f"Request {ticket.ticket_number} submitted.")
            return redirect("portal:ticket_detail", pk=ticket.pk)
        messages.error(request, "Title is required.")
    return render(
        request,
        "portal/new_request.html",
        {"title": "New request", "catalog": catalog},
    )


@login_required
def portal_catalog(request):
    company = require_company(request)
    return render(
        request,
        "portal/catalog.html",
        {"title": "Service catalog", "catalog": PortalService.catalog(company)},
    )


@login_required
def portal_knowledge(request):
    company = get_active_company(request)
    q = request.GET.get("q", "")
    articles = PortalService.knowledge(company, q)
    page = Paginator(articles, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "portal/knowledge.html",
        {"title": "Help center", "page": page, "q": q},
    )


@login_required
@require_POST
def portal_comment(request, pk: int):
    ticket = get_object_or_404(PortalService.my_tickets(request.user), pk=pk)
    body = (request.POST.get("body") or "").strip()
    if body:
        TicketService.add_comment(ticket, body=body, author=request.user, is_internal=False)
        messages.success(request, "Comment added.")
    return redirect("portal:ticket_detail", pk=pk)


class PortalHomeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        profile = PortalService.ensure_profile(request.user, company)
        return Response(
            {
                "profile": PortalProfileSerializer(profile).data,
                "tickets": PortalTicketSerializer(
                    PortalService.my_tickets(request.user, company)[:20], many=True
                ).data,
                "catalog": PortalCatalogSerializer(
                    PortalService.catalog(company), many=True
                ).data,
                "announcements": PortalAnnouncementSerializer(
                    PortalService.announcements(company), many=True
                ).data,
                "knowledge": PortalKnowledgeSerializer(
                    list(PortalService.knowledge(company)[:10]), many=True
                ).data,
            }
        )


class PortalTicketAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        company = get_active_company(request)
        if pk is None:
            qs = PortalService.my_tickets(request.user, company)
            return Response(PortalTicketSerializer(qs[:100], many=True).data)
        ticket = get_object_or_404(PortalService.my_tickets(request.user, company), pk=pk)
        return Response(PortalTicketDetailSerializer(ticket).data)

    def post(self, request):
        ser = PortalRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        rt = None
        if ser.validated_data.get("request_type_id"):
            rt = RequestType.objects.filter(
                pk=ser.validated_data["request_type_id"],
                department__company=company,
            ).first()
        ticket = PortalService.create_request(
            request.user,
            company,
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description") or "",
            request_type=rt,
        )
        return Response(
            PortalTicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED
        )