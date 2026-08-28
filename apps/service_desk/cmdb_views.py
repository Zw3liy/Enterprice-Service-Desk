"""
apps/service_desk/cmdb_views.py

CMDB (Configuration Management Database).

New flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms.cmdb_forms import ConfigurationItemForm
from .models import CIRelationship, ConfigurationItem
from .security.mixins import (
    ConfigurationItemChangePermissionMixin,
    ConfigurationItemCreatePermissionMixin,
    ConfigurationItemViewPermissionMixin,
)
from .security.policies import (
    get_change_queryset,
    get_configuration_item_queryset,
    get_ticket_queryset,
)
from .selectors.cmdb_selector import CMDBSelector
from .services.cmdb_service import CMDBService


class ConfigurationItemListView(
    ConfigurationItemViewPermissionMixin,
    ListView
):
    model = ConfigurationItem
    template_name = "cmdb/list.html"
    context_object_name = "items"
    paginate_by = 25
    permission_required = ("service_desk.view_configurationitem",)

    def get_queryset(self):
        queryset = CMDBSelector.with_related(
            get_configuration_item_queryset(self.request.user)
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = CMDBSelector.search(queryset, search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = CMDBSelector.scoped_summary(
            get_configuration_item_queryset(self.request.user)
        )
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["status_choices"] = ConfigurationItem.STATUS_CHOICES
        return context


class ConfigurationItemCreateView(
    ConfigurationItemCreatePermissionMixin,
    CreateView
):
    model = ConfigurationItem
    form_class = ConfigurationItemForm
    template_name = "cmdb/create.html"
    permission_required = ("service_desk.add_configurationitem",)
    success_url = reverse_lazy("service_desk:cmdb_item_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = CMDBService.create_ci(
                user=self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, f"Configuration item '{self.object}' created.")
        return redirect("service_desk:cmdb_item_detail", pk=self.object.pk)


class ConfigurationItemDetailView(
    ConfigurationItemViewPermissionMixin,
    DetailView
):
    model = ConfigurationItem
    template_name = "cmdb/detail.html"
    context_object_name = "item"
    permission_required = ("service_desk.view_configurationitem",)

    def get_queryset(self):
        return CMDBSelector.with_related(
            get_configuration_item_queryset(self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["outgoing_relationships"] = self.object.outgoing_relationships.select_related(
            "target", "created_by"
        )
        context["incoming_relationships"] = self.object.incoming_relationships.select_related(
            "source", "created_by"
        )
        context["relationship_types"] = CIRelationship.TYPE_CHOICES
        context["linked_tickets"] = self.object.tickets.all()
        context["linked_changes"] = self.object.changes.all()

        context["candidate_items"] = get_configuration_item_queryset(
            self.request.user
        ).exclude(pk=self.object.pk)
        context["candidate_tickets"] = get_ticket_queryset(
            self.request.user
        ).exclude(pk__in=self.object.tickets.values("pk"))
        context["candidate_changes"] = get_change_queryset(
            self.request.user
        ).exclude(pk__in=self.object.changes.values("pk"))

        return context


class ConfigurationItemUpdateView(
    ConfigurationItemChangePermissionMixin,
    UpdateView
):
    model = ConfigurationItem
    form_class = ConfigurationItemForm
    template_name = "cmdb/update.html"
    context_object_name = "item"
    permission_required = ("service_desk.change_configurationitem",)

    def get_queryset(self):
        return get_configuration_item_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        persisted = ConfigurationItem.objects.get(pk=self.object.pk)

        try:
            self.object = CMDBService.update_ci(
                persisted, user=self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Configuration item updated.")
        return redirect("service_desk:cmdb_item_detail", pk=self.object.pk)


class CIRelationshipAddView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk):
        source = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        target = get_object_or_404(
            get_configuration_item_queryset(request.user),
            pk=request.POST.get("target_id"),
        )

        try:
            CMDBService.add_relationship(
                source,
                target,
                request.POST.get("relationship_type", ""),
                user=request.user,
            )
            messages.success(request, "Relationship added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:cmdb_item_detail", pk=source.pk)


class CIRelationshipRemoveView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk, relationship_pk):
        source = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        relationship = get_object_or_404(
            CIRelationship, pk=relationship_pk, source=source
        )

        CMDBService.remove_relationship(relationship)
        messages.success(request, "Relationship removed.")

        return redirect("service_desk:cmdb_item_detail", pk=source.pk)


class CILinkTicketView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk):
        ci = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        ticket = get_object_or_404(
            get_ticket_queryset(request.user),
            pk=request.POST.get("ticket_id"),
        )

        CMDBService.link_ticket(ci, ticket)
        messages.success(request, f"Linked ticket #{ticket.pk}.")

        return redirect("service_desk:cmdb_item_detail", pk=ci.pk)


class CIUnlinkTicketView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk, ticket_pk):
        ci = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        ticket = get_object_or_404(
            get_ticket_queryset(request.user), pk=ticket_pk
        )

        CMDBService.unlink_ticket(ci, ticket)
        messages.success(request, f"Unlinked ticket #{ticket.pk}.")

        return redirect("service_desk:cmdb_item_detail", pk=ci.pk)


class CILinkChangeView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk):
        ci = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        change = get_object_or_404(
            get_change_queryset(request.user),
            pk=request.POST.get("change_id"),
        )

        CMDBService.link_change(ci, change)
        messages.success(request, f"Linked change '{change}'.")

        return redirect("service_desk:cmdb_item_detail", pk=ci.pk)


class CIUnlinkChangeView(ConfigurationItemChangePermissionMixin, View):
    def post(self, request, pk, change_pk):
        ci = get_object_or_404(
            get_configuration_item_queryset(request.user), pk=pk
        )
        change = get_object_or_404(
            get_change_queryset(request.user), pk=change_pk
        )

        CMDBService.unlink_change(ci, change)
        messages.success(request, f"Unlinked change '{change}'.")

        return redirect("service_desk:cmdb_item_detail", pk=ci.pk)
