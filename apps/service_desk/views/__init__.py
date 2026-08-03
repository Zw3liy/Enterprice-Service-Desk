"""HTTP views for Enterprise Service Desk (technician + portal UI)."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import TemplateView

from apps.service_desk.forms import (
    AssignForm,
    AttachmentForm,
    CommentForm,
    FeedbackForm,
    KnowledgeArticleForm,
    LoginForm,
    RegisterForm,
    TicketCreateForm,
    TicketFilterForm,
    TicketUpdateForm,
    WorkLogForm,
    AssetForm,
)
from apps.service_desk.forms_dynamic import build_dynamic_form
from apps.service_desk.models import (
    Asset,
    Company,
    CustomerFeedback,
    KnowledgeArticle,
    Notification,
    Ticket,
)
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.services.assignment_service import AssignmentService
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.services.knowledge_service import KnowledgeService
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company, require_company

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class ServiceDeskLoginView(LoginView):
    template_name = "service_desk/auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class ServiceDeskLogoutView(LogoutView):
    next_page = reverse_lazy("login")


@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("service_desk:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data["email"]
        user.first_name = form.cleaned_data.get("first_name", "")
        user.last_name = form.cleaned_data.get("last_name", "")
        user.save()
        login(request, user)
        messages.success(request, "Welcome to Enterprise Service Desk.")
        return redirect("service_desk:dashboard")
    return render(request, "service_desk/auth/register.html", {"form": form})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@method_decorator(login_required, name="dispatch")
class DashboardView(TemplateView):
    template_name = "service_desk/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = get_active_company(self.request)
        summary = DashboardService.summary(company=company, user=self.request.user)
        ctx.update(
            {
                "title": "Operations Dashboard",
                "company": company,
                "summary": summary,
                "recent_tickets": DashboardService.recent_tickets(company=company, limit=12),
                **summary,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


@login_required
def ticket_list(request: HttpRequest) -> HttpResponse:
    company = get_active_company(request)
    form = TicketFilterForm(request.GET or None, company=company)
    filters = {
        "company": company,
        "query": request.GET.get("q", ""),
        "status_id": request.GET.get("status") or None,
        "priority_id": request.GET.get("priority") or None,
        "queue_id": request.GET.get("queue") or None,
        "ticket_type": request.GET.get("ticket_type") or "",
        "open_only": request.GET.get("open_only") in {"1", "true", "on", None}
        if "open_only" not in request.GET
        else request.GET.get("open_only") in {"1", "true", "on"},
        "mine_user": request.user if request.GET.get("mine") in {"1", "true", "on"} else None,
    }
    # Default open_only true when no query string
    if not request.GET:
        filters["open_only"] = True
    qs = TicketService.search(**filters)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "service_desk/tickets/list.html",
        {
            "title": "Tickets",
            "page": page,
            "filter_form": form,
            "company": company,
            "tickets": page.object_list,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request: HttpRequest) -> HttpResponse:
    company = require_company(request)
    form = TicketCreateForm(request.POST or None, company=company)
    dynamic = None
    request_type = None
    if request.method == "POST":
        rt_id = request.POST.get("request_type")
        if rt_id:
            from apps.service_desk.models import RequestType

            request_type = RequestType.objects.filter(pk=rt_id).first()
            dynamic = build_dynamic_form(request_type, data=request.POST)
        if form.is_valid() and (dynamic is None or dynamic.is_valid()):
            try:
                custom_values = dynamic.cleaned_data if dynamic else {}
                ticket = TicketService.create_ticket(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description") or "",
                    company=company,
                    department=form.cleaned_data.get("department"),
                    request_type=form.cleaned_data.get("request_type"),
                    category=form.cleaned_data.get("category"),
                    priority=form.cleaned_data.get("priority"),
                    queue=form.cleaned_data.get("queue"),
                    ticket_type=form.cleaned_data.get("ticket_type")
                    or Ticket.TicketType.INCIDENT,
                    channel=form.cleaned_data.get("channel") or Ticket.Channel.PORTAL,
                    custom_field_values=custom_values,
                    tags=form.cleaned_data.get("tags") or [],
                    impact=form.cleaned_data.get("impact") or 3,
                    urgency=form.cleaned_data.get("urgency") or 3,
                    requester_user=request.user,
                    actor=request.user,
                    auto_assign=bool(request.POST.get("auto_assign")),
                )
                messages.success(request, f"Ticket {ticket.ticket_number} created.")
                return redirect("service_desk:ticket_detail", pk=ticket.pk)
            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errs in exc.message_dict.items():
                        for err in errs:
                            form.add_error(None, f"{field}: {err}")
                else:
                    form.add_error(None, exc)
    else:
        dynamic = build_dynamic_form(None)

    return render(
        request,
        "service_desk/tickets/create.html",
        {
            "title": "Create ticket",
            "form": form,
            "dynamic_form": dynamic,
            "company": company,
        },
    )


@login_required
def ticket_detail(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(TicketService.base_queryset(), pk=pk)
    company = ticket.company or get_active_company(request)
    comment_form = CommentForm()
    worklog_form = WorkLogForm()
    assign_form = AssignForm(company=company)
    attachment_form = AttachmentForm()
    update_form = TicketUpdateForm(instance=ticket, company=company)
    feedback_form = FeedbackForm()
    articles = AIService.recommend_articles(ticket)
    return render(
        request,
        "service_desk/tickets/detail.html",
        {
            "title": ticket.ticket_number,
            "ticket": ticket,
            "company": company,
            "comment_form": comment_form,
            "worklog_form": worklog_form,
            "assign_form": assign_form,
            "attachment_form": attachment_form,
            "update_form": update_form,
            "feedback_form": feedback_form,
            "recommended_articles": articles,
            "comments": ticket.comments.select_related("author").all(),
            "work_logs": ticket.work_logs.select_related("author").all(),
            "attachments": ticket.attachments.all(),
            "audit_logs": ticket.audit_logs.select_related("actor")[:50],
            "escalations": ticket.escalations.all()[:20],
        },
    )


@login_required
@require_POST
def ticket_update(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TicketUpdateForm(request.POST, instance=ticket, company=ticket.company)
    if form.is_valid():
        try:
            TicketService.update_ticket(
                ticket,
                actor=request.user,
                **{k: form.cleaned_data[k] for k in form.cleaned_data},
            )
            messages.success(request, "Ticket updated.")
        except ValidationError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Please correct the errors in the form.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_comment(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        TicketService.add_comment(
            ticket,
            body=form.cleaned_data["body"],
            author=request.user,
            is_internal=form.cleaned_data.get("is_internal") or False,
        )
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Comment could not be added.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_worklog(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = WorkLogForm(request.POST)
    if form.is_valid():
        TicketService.add_work_log(
            ticket,
            description=form.cleaned_data["description"],
            minutes_spent=form.cleaned_data["minutes_spent"],
            author=request.user,
            is_billable=form.cleaned_data.get("is_billable") or False,
        )
        messages.success(request, "Work log recorded.")
    else:
        messages.error(request, "Invalid work log.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_assign(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = AssignForm(request.POST, company=ticket.company)
    if form.is_valid():
        if form.cleaned_data.get("auto_assign"):
            AssignmentService.auto_assign(ticket, assigned_by=request.user)
        else:
            AssignmentService.assign(
                ticket,
                assignee=form.cleaned_data.get("assignee"),
                queue=form.cleaned_data.get("queue"),
                assigned_by=request.user,
                note=form.cleaned_data.get("note") or "",
            )
        messages.success(request, "Assignment updated.")
    else:
        messages.error(request, "Assignment failed.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_attach(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        TicketService.add_attachment(
            ticket,
            uploaded_file=form.cleaned_data["file"],
            uploaded_by=request.user,
        )
        messages.success(request, "Attachment uploaded.")
    else:
        messages.error(request, "Upload failed.")
    return redirect("service_desk:ticket_detail", pk=pk)


@login_required
@require_POST
def ticket_feedback(request: HttpRequest, pk: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=pk)
    form = FeedbackForm(request.POST)
    if form.is_valid():
        CustomerFeedback.objects.update_or_create(
            ticket=ticket,
            defaults={
                "rating": form.cleaned_data["rating"],
                "comment": form.cleaned_data.get("comment") or "",
                "submitted_by": ticket.requester,
            },
        )
        messages.success(request, "Thank you for your feedback.")
    else:
        messages.error(request, "Invalid feedback.")
    return redirect("service_desk:ticket_detail", pk=pk)


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------


@login_required
def knowledge_list(request: HttpRequest) -> HttpResponse:
    company = get_active_company(request)
    q = request.GET.get("q", "")
    articles = KnowledgeService.search(
        q, company=company, include_internal=request.user.is_staff
    )
    page = Paginator(articles, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "service_desk/knowledge/list.html",
        {"title": "Knowledge Base", "page": page, "q": q, "company": company},
    )


@login_required
def knowledge_detail(request: HttpRequest, slug: str) -> HttpResponse:
    company = get_active_company(request)
    qs = KnowledgeArticle.objects.all()
    if company:
        qs = qs.filter(company=company)
    article = get_object_or_404(qs, slug=slug)
    if article.is_internal and not request.user.is_staff:
        return HttpResponseForbidden("Internal article")
    KnowledgeService.record_view(article)
    article.refresh_from_db()
    return render(
        request,
        "service_desk/knowledge/detail.html",
        {"title": article.title, "article": article},
    )


@login_required
@require_http_methods(["GET", "POST"])
def knowledge_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff only")
    company = require_company(request)
    form = KnowledgeArticleForm(request.POST or None, company=company)
    if request.method == "POST" and form.is_valid():
        article = form.save(commit=False)
        article.company = company
        article.author = request.user
        article.save()
        messages.success(request, "Article saved.")
        return redirect("service_desk:knowledge_detail", slug=article.slug)
    return render(
        request,
        "service_desk/knowledge/form.html",
        {"title": "New article", "form": form},
    )


@login_required
@require_POST
def knowledge_feedback(request: HttpRequest, slug: str) -> HttpResponse:
    article = get_object_or_404(KnowledgeArticle, slug=slug)
    helpful = request.POST.get("helpful") == "1"
    KnowledgeService.feedback(article, helpful=helpful)
    messages.success(request, "Thanks for the feedback.")
    return redirect("service_desk:knowledge_detail", slug=slug)


# ---------------------------------------------------------------------------
# Assets / CMDB lite
# ---------------------------------------------------------------------------


@login_required
def asset_list(request: HttpRequest) -> HttpResponse:
    company = get_active_company(request)
    qs = Asset.objects.select_related("department", "owner").order_by("asset_tag")
    if company:
        qs = qs.filter(company=company)
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(asset_tag__icontains=q)
            | Q(serial_number__icontains=q)
            | Q(location__icontains=q)
        )
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "service_desk/assets/list.html",
        {"title": "CMDB Assets", "page": page, "q": q},
    )


@login_required
def asset_detail(request: HttpRequest, pk: int) -> HttpResponse:
    asset = get_object_or_404(
        Asset.objects.select_related("company", "department", "owner"), pk=pk
    )
    return render(
        request,
        "service_desk/assets/detail.html",
        {
            "title": asset.asset_tag,
            "asset": asset,
            "related_tickets": asset.tickets.select_related("status", "priority")[:20],
            "relations": asset.outbound_relations.select_related("target").all(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def asset_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff only")
    company = require_company(request)
    form = AssetForm(request.POST or None, company=company)
    if request.method == "POST" and form.is_valid():
        asset = form.save(commit=False)
        asset.company = company
        asset.save()
        messages.success(request, f"Asset {asset.asset_tag} created.")
        return redirect("service_desk:asset_detail", pk=asset.pk)
    return render(
        request,
        "service_desk/assets/form.html",
        {"title": "New asset", "form": form},
    )


# ---------------------------------------------------------------------------
# Reports / notifications / health
# ---------------------------------------------------------------------------


@login_required
def reports_index(request: HttpRequest) -> HttpResponse:
    company = get_active_company(request)
    summary = DashboardService.summary(company=company, user=request.user)
    return render(
        request,
        "service_desk/reports/index.html",
        {"title": "Reports & Analytics", "summary": summary, "company": company},
    )


@login_required
def notification_list(request: HttpRequest) -> HttpResponse:
    qs = Notification.objects.filter(recipient=request.user).select_related("ticket")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(
        request,
        "service_desk/notifications/list.html",
        {"title": "Notifications", "page": page},
    )


@login_required
@require_POST
def notification_read(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    note.mark_read()
    next_url = request.POST.get("next") or reverse("service_desk:notifications")
    return redirect(next_url)


@login_required
def api_dashboard_json(request: HttpRequest) -> JsonResponse:
    company = get_active_company(request)
    return JsonResponse(DashboardService.summary(company=company, user=request.user))


def healthz(request: HttpRequest) -> JsonResponse:
    from django.db import connection

    db_ok = True
    try:
        connection.ensure_connection()
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        logger.error("healthz db failure: %s", exc)
    status = 200 if db_ok else 503
    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "database": db_ok,
            "service": "enterprise-service-desk",
        },
        status=status,
    )


def readiness(request: HttpRequest) -> JsonResponse:
    has_company = Company.objects.filter(is_active=True).exists()
    return JsonResponse(
        {"ready": has_company, "companies": Company.objects.count()},
        status=200 if has_company else 503,
    )
