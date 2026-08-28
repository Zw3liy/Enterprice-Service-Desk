"""
apps/service_desk/reporting_views.py

Reporting and Analytics.

New flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2.

Every dashboard section and every export reads through the exact
same RBAC-scoped queryset function the owning module's own views
use (get_ticket_queryset, get_change_queryset, ...) — reporting has
no separate, wider data path, so a Requester's report is scoped
exactly like their ticket list, a Manager's to their department, and
so on. All figures are live query results as of the moment the page
is rendered; there is no separate historical-snapshot store in this
codebase, so every card is labelled "Live" with the generation
timestamp rather than implying a cached/batched figure.
"""

from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .models import Department, TicketSLA
from .security.mixins import ServiceDeskLoginRequiredMixin
from .security.policies import (
    get_change_queryset,
    get_configuration_item_queryset,
    get_knowledge_article_queryset,
    get_release_queryset,
    get_service_request_queryset,
    get_ticket_queryset,
    is_administrator,
    is_manager,
)
from .selectors.change_selector import ChangeSelector
from .selectors.cmdb_selector import CMDBSelector
from .selectors.knowledge_selector import KnowledgeSelector
from .selectors.release_selector import ReleaseSelector
from .selectors.service_request_selector import ServiceRequestSelector
from .services.reporting_service import parse_date_range, stream_csv


def _filtered(queryset, date_from, date_to, department_id, date_field, dept_field):
    if date_from:
        queryset = queryset.filter(**{f"{date_field}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{date_field}__lte": date_to})
    if department_id and dept_field:
        queryset = queryset.filter(**{f"{dept_field}_id": department_id})
    return queryset


class ReportingDashboardView(ServiceDeskLoginRequiredMixin, TemplateView):
    """
    One scoped dashboard covering every module — each section is
    only computed (and only rendered) if the viewer holds that
    module's own view permission, exactly mirroring the sidebar's own
    gating.
    """

    template_name = "reporting/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        date_from, date_to = parse_date_range(self.request)
        department_id = self.request.GET.get("department", "").strip()

        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        context["department_filter"] = department_id
        context["generated_at"] = timezone.now()

        if is_administrator(user):
            context["available_departments"] = Department.objects.all()
        elif is_manager(user):
            context["available_departments"] = user.managed_departments.all()
        else:
            context["available_departments"] = Department.objects.none()

        if user.has_perm("service_desk.view_ticket"):
            tickets = _filtered(
                get_ticket_queryset(user), date_from, date_to,
                department_id, "created_at", "department",
            )
            context["ticket_stats"] = tickets.aggregate(
                total=Count("pk"),
                open=Count("pk", filter=Q(status="open")),
                in_progress=Count("pk", filter=Q(status="in_progress")),
                closed=Count("pk", filter=Q(status="closed")),
                high_priority=Count(
                    "pk", filter=Q(priority__in=["high", "urgent"])
                ),
            )

            sla_qs = TicketSLA.objects.filter(
                ticket__in=get_ticket_queryset(user)
            )
            context["sla_stats"] = sla_qs.aggregate(
                total=Count("pk"),
                response_breached=Count(
                    "pk", filter=Q(response_breached=True)
                ),
                resolution_breached=Count(
                    "pk", filter=Q(resolution_breached=True)
                ),
            )

        if user.has_perm("service_desk.view_servicerequest"):
            requests_qs = _filtered(
                get_service_request_queryset(user), date_from, date_to,
                department_id, "created_at", "ticket__department",
            )
            context["request_stats"] = ServiceRequestSelector.scoped_summary(
                requests_qs
            )

        if user.has_perm("service_desk.view_change"):
            changes = _filtered(
                get_change_queryset(user), date_from, date_to,
                department_id, "created_at", "department",
            )
            context["change_stats"] = ChangeSelector.scoped_summary(changes)

        if user.has_perm("service_desk.view_release"):
            releases = _filtered(
                get_release_queryset(user), date_from, date_to,
                department_id, "created_at", "department",
            )
            context["release_stats"] = ReleaseSelector.scoped_summary(releases)

        if user.has_perm("service_desk.view_configurationitem"):
            cis = _filtered(
                get_configuration_item_queryset(user), date_from, date_to,
                department_id, "created_at", "department",
            )
            context["cmdb_stats"] = CMDBSelector.scoped_summary(cis)

        if user.has_perm("service_desk.view_knowledgearticle"):
            articles = _filtered(
                get_knowledge_article_queryset(user), date_from, date_to,
                None, "created_at", None,
            )
            context["knowledge_stats"] = KnowledgeSelector.scoped_summary(
                articles
            )

        return context


class TicketExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        department_id = request.GET.get("department", "").strip()

        if not request.user.has_perm("service_desk.view_ticket"):
            raise PermissionDenied

        queryset = _filtered(
            get_ticket_queryset(request.user), date_from, date_to,
            department_id, "created_at", "department",
        ).select_related("department", "assigned_to", "created_by")

        rows = (
            (
                t.pk, t.title, t.status, t.priority, t.urgency,
                t.department.name if t.department else "",
                t.assigned_to.get_username() if t.assigned_to else "",
                t.created_by.get_username() if t.created_by else "",
                t.created_at.isoformat(),
            )
            for t in queryset.iterator()
        )

        return stream_csv(
            "tickets.csv",
            ["ID", "Title", "Status", "Priority", "Urgency", "Department", "Assigned To", "Created By", "Created At"],
            rows,
        )


class ServiceRequestExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("service_desk.view_servicerequest"):
            raise PermissionDenied

        date_from, date_to = parse_date_range(request)
        department_id = request.GET.get("department", "").strip()

        queryset = _filtered(
            get_service_request_queryset(request.user), date_from, date_to,
            department_id, "created_at", "ticket__department",
        ).select_related("catalog_item", "ticket", "ticket__department")

        rows = (
            (
                sr.pk, sr.catalog_item.name, sr.status, sr.quantity,
                sr.ticket.department.name if sr.ticket.department else "",
                sr.created_at.isoformat(),
            )
            for sr in queryset.iterator()
        )

        return stream_csv(
            "service_requests.csv",
            ["ID", "Item", "Status", "Quantity", "Department", "Created At"],
            rows,
        )


class ChangeExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("service_desk.view_change"):
            raise PermissionDenied

        date_from, date_to = parse_date_range(request)
        department_id = request.GET.get("department", "").strip()

        queryset = _filtered(
            get_change_queryset(request.user), date_from, date_to,
            department_id, "created_at", "department",
        ).select_related("department", "assigned_to")

        rows = (
            (
                c.pk, c.title, c.change_type, c.status,
                c.risk_level or "", c.department.name if c.department else "",
                c.assigned_to.get_username() if c.assigned_to else "",
                c.created_at.isoformat(),
            )
            for c in queryset.iterator()
        )

        return stream_csv(
            "changes.csv",
            ["ID", "Title", "Type", "Status", "Risk", "Department", "Assigned To", "Created At"],
            rows,
        )


class ReleaseExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("service_desk.view_release"):
            raise PermissionDenied

        date_from, date_to = parse_date_range(request)
        department_id = request.GET.get("department", "").strip()

        queryset = _filtered(
            get_release_queryset(request.user), date_from, date_to,
            department_id, "created_at", "department",
        ).select_related("department", "owner")

        rows = (
            (
                r.pk, r.name, r.version, r.environment, r.status,
                r.department.name if r.department else "",
                r.owner.get_username() if r.owner else "",
                r.created_at.isoformat(),
            )
            for r in queryset.iterator()
        )

        return stream_csv(
            "releases.csv",
            ["ID", "Name", "Version", "Environment", "Status", "Department", "Owner", "Created At"],
            rows,
        )


class ConfigurationItemExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("service_desk.view_configurationitem"):
            raise PermissionDenied

        date_from, date_to = parse_date_range(request)
        department_id = request.GET.get("department", "").strip()

        queryset = _filtered(
            get_configuration_item_queryset(request.user), date_from, date_to,
            department_id, "created_at", "department",
        ).select_related("ci_type", "department", "owner")

        rows = (
            (
                ci.pk, ci.name, ci.identifier, ci.ci_type.name, ci.status,
                ci.criticality, ci.department.name if ci.department else "",
                ci.owner.get_username() if ci.owner else "",
            )
            for ci in queryset.iterator()
        )

        return stream_csv(
            "configuration_items.csv",
            ["ID", "Name", "Identifier", "Type", "Status", "Criticality", "Department", "Owner"],
            rows,
        )


class KnowledgeArticleExportView(ServiceDeskLoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("service_desk.view_knowledgearticle"):
            raise PermissionDenied

        date_from, date_to = parse_date_range(request)

        queryset = _filtered(
            get_knowledge_article_queryset(request.user), date_from, date_to,
            None, "created_at", None,
        ).select_related("category", "author")

        rows = (
            (
                a.pk, a.title, a.category.name, a.status, a.visibility,
                a.version, a.author.get_username() if a.author else "",
            )
            for a in queryset.iterator()
        )

        return stream_csv(
            "knowledge_articles.csv",
            ["ID", "Title", "Category", "Status", "Visibility", "Version", "Author"],
            rows,
        )
