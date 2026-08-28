"""
apps/service_desk/catalog_views.py

Service Catalogue and Service Request Management.

A new flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2, for why (matches the
per-capability file convention already used by services/selectors/
forms, and introduces no flat-file/package collision).
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms.service_catalog_forms import (
    CatalogItemForm,
    ServiceRequestCreateForm,
)
from .models import CatalogItem, ServiceRequest
from .security.mixins import (
    CatalogItemChangePermissionMixin,
    CatalogItemCreatePermissionMixin,
    CatalogItemViewPermissionMixin,
    ServiceRequestChangePermissionMixin,
    ServiceRequestCreatePermissionMixin,
    ServiceRequestViewPermissionMixin,
)
from .security.policies import (
    get_catalog_item_queryset,
    get_service_request_queryset,
)
from .selectors.service_catalog_selector import CatalogSelector
from .selectors.service_request_selector import ServiceRequestSelector
from .services.service_catalog_service import CatalogService
from .services.service_request_service import ServiceRequestService

User = get_user_model()


# ======================================================
# Catalogue browsing
# ======================================================


class CatalogItemListView(
    CatalogItemViewPermissionMixin,
    ListView
):
    """
    Browse the service catalogue.

    Visibility controlled by security.policies.get_catalog_item_queryset —
    active items for everyone, plus inactive ones for Manager/Admin
    who administer the catalogue.
    """

    model = CatalogItem
    template_name = "catalog/list.html"
    context_object_name = "items"
    paginate_by = 25
    permission_required = ("service_desk.view_catalogitem",)

    def get_queryset(self):
        queryset = get_catalog_item_queryset(
            self.request.user
        ).select_related("category", "fulfillment_department")

        category_id = self.request.GET.get("category", "").strip()
        if category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = CatalogSelector.search(search).filter(
                pk__in=queryset.values("pk")
            )

        return queryset.order_by("category__name", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = CatalogSelector.scoped_summary(
            get_catalog_item_queryset(self.request.user)
        )
        context["search_query"] = self.request.GET.get("q", "")
        context["category_filter"] = self.request.GET.get("category", "")
        return context


class CatalogItemDetailView(
    CatalogItemViewPermissionMixin,
    DetailView
):
    model = CatalogItem
    template_name = "catalog/detail.html"
    context_object_name = "item"
    permission_required = ("service_desk.view_catalogitem",)

    def get_queryset(self):
        return get_catalog_item_queryset(
            self.request.user
        ).select_related("category", "fulfillment_department")


# ======================================================
# Catalogue administration
# ======================================================


class CatalogItemCreateView(
    CatalogItemCreatePermissionMixin,
    CreateView
):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = "catalog/item_create.html"
    permission_required = ("service_desk.add_catalogitem",)
    success_url = reverse_lazy("service_desk:catalog_item_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = CatalogService.create_item(
                user=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request, f"Catalogue item '{self.object.name}' created."
        )
        return redirect("service_desk:catalog_item_detail", pk=self.object.pk)


class CatalogItemUpdateView(
    CatalogItemChangePermissionMixin,
    UpdateView
):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = "catalog/item_update.html"
    context_object_name = "item"
    permission_required = ("service_desk.change_catalogitem",)

    def get_queryset(self):
        return get_catalog_item_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        persisted = CatalogItem.objects.get(pk=self.object.pk)

        try:
            self.object = CatalogService.update_item(
                persisted,
                user=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Catalogue item updated.")
        return redirect("service_desk:catalog_item_detail", pk=self.object.pk)


class CatalogItemDeactivateView(
    CatalogItemChangePermissionMixin,
    View
):
    def post(self, request, pk):
        item = get_object_or_404(
            get_catalog_item_queryset(request.user), pk=pk
        )

        try:
            CatalogService.deactivate_item(item)
            messages.success(request, f"'{item.name}' deactivated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:catalog_item_detail", pk=item.pk)


class CatalogItemActivateView(
    CatalogItemChangePermissionMixin,
    View
):
    def post(self, request, pk):
        item = get_object_or_404(
            get_catalog_item_queryset(request.user), pk=pk
        )

        try:
            CatalogService.activate_item(item)
            messages.success(request, f"'{item.name}' reactivated.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:catalog_item_detail", pk=item.pk)


# ======================================================
# Service requests
# ======================================================


class ServiceRequestCreateView(
    ServiceRequestCreatePermissionMixin,
    View
):
    """
    Submit a request for one catalogue item.

    The item is resolved through get_catalog_item_queryset before use
    so an inactive or otherwise unavailable item cannot be requested
    by guessing its primary key.
    """

    permission_required = ("service_desk.add_servicerequest",)

    def get(self, request, item_pk):
        item = get_object_or_404(
            get_catalog_item_queryset(request.user).filter(is_active=True),
            pk=item_pk,
        )
        form = ServiceRequestCreateForm()
        return self._render(request, item, form)

    def post(self, request, item_pk):
        item = get_object_or_404(
            get_catalog_item_queryset(request.user).filter(is_active=True),
            pk=item_pk,
        )
        form = ServiceRequestCreateForm(request.POST)

        if not form.is_valid():
            return self._render(request, item, form)

        try:
            service_request = ServiceRequestService.create_request(
                item,
                request.user,
                quantity=form.cleaned_data["quantity"],
                justification=form.cleaned_data["justification"],
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self._render(request, item, form)

        messages.success(request, "Service request submitted.")
        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )

    @staticmethod
    def _render(request, item, form):
        return render(
            request,
            "catalog/request_create.html",
            {"item": item, "form": form},
        )


class ServiceRequestListView(
    ServiceRequestViewPermissionMixin,
    ListView
):
    model = ServiceRequest
    template_name = "catalog/request_list.html"
    context_object_name = "service_requests"
    paginate_by = 25
    permission_required = ("service_desk.view_servicerequest",)

    def get_queryset(self):
        queryset = ServiceRequestSelector.with_related(
            get_service_request_queryset(self.request.user)
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = ServiceRequestSelector.scoped_summary(
            get_service_request_queryset(self.request.user)
        )
        context["status_filter"] = self.request.GET.get("status", "")
        context["status_choices"] = ServiceRequest.STATUS_CHOICES
        return context


class ServiceRequestDetailView(
    ServiceRequestViewPermissionMixin,
    DetailView
):
    model = ServiceRequest
    template_name = "catalog/request_detail.html"
    context_object_name = "service_request"
    permission_required = ("service_desk.view_servicerequest",)

    def get_queryset(self):
        return ServiceRequestSelector.with_related(
            get_service_request_queryset(self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approvals"] = self.object.approvals.select_related("actor")
        context["history"] = self.object.history.select_related(
            "performed_by"
        )
        context["available_technicians"] = User.objects.filter(
            groups__name="Technician",
            is_active=True,
        ).order_by("username")
        context["next_statuses"] = ServiceRequestService.STATUS_FLOW.get(
            self.object.status, []
        )
        return context


class ServiceRequestApproveView(
    ServiceRequestChangePermissionMixin,
    View
):
    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        try:
            ServiceRequestService.approve_request(
                service_request,
                request.user,
                comment=request.POST.get("comment", ""),
            )
            messages.success(request, "Service request approved.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )


class ServiceRequestRejectView(
    ServiceRequestChangePermissionMixin,
    View
):
    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        try:
            ServiceRequestService.reject_request(
                service_request,
                request.user,
                comment=request.POST.get("comment", ""),
            )
            messages.success(request, "Service request rejected.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )


class ServiceRequestAssignView(
    ServiceRequestChangePermissionMixin,
    View
):
    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        technician = get_object_or_404(
            User,
            pk=request.POST.get("technician_id"),
            is_active=True,
        )

        try:
            ServiceRequestService.assign_request(
                service_request, technician, user=request.user
            )
            messages.success(
                request,
                f"Request assigned to {technician.get_username()}.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )


class ServiceRequestMarkFulfillingView(
    ServiceRequestChangePermissionMixin,
    View
):
    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        try:
            ServiceRequestService.mark_fulfilling(
                service_request, user=request.user
            )
            messages.success(request, "Request marked as fulfilling.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )


class ServiceRequestMarkFulfilledView(
    ServiceRequestChangePermissionMixin,
    View
):
    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        try:
            ServiceRequestService.mark_fulfilled(
                service_request, user=request.user
            )
            messages.success(
                request,
                "Request fulfilled — awaiting requester confirmation.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )


class ServiceRequestCancelView(
    ServiceRequestViewPermissionMixin,
    View
):
    """
    Cancel a service request.

    Gated on view_servicerequest (Requesters hold it) rather than
    change_servicerequest — the real gate is "are you the requester,
    a manager or an administrator", enforced in the service layer,
    the same shape ADR-010 used for requester ticket confirmation.
    """

    permission_required = ("service_desk.view_servicerequest",)

    def post(self, request, pk):
        service_request = get_object_or_404(
            get_service_request_queryset(request.user), pk=pk
        )

        try:
            ServiceRequestService.cancel_request(
                service_request,
                request.user,
                reason=request.POST.get("reason", ""),
            )
            messages.success(request, "Service request cancelled.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect(
            "service_desk:service_request_detail", pk=service_request.pk
        )
