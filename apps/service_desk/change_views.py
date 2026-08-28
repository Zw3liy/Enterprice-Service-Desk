"""
apps/service_desk/change_views.py

Change Management.

New flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms.change_forms import (
    ChangeAssessmentForm,
    ChangeCreateForm,
    ChangeScheduleForm,
)
from .models import Change
from .security.mixins import (
    ChangeChangePermissionMixin,
    ChangeCreatePermissionMixin,
    ChangeViewPermissionMixin,
)
from .security.policies import get_change_queryset
from .selectors.change_selector import ChangeSelector
from .services.change_service import ChangeService

User = get_user_model()


class ChangeListView(
    ChangeViewPermissionMixin,
    ListView
):
    model = Change
    template_name = "changes/list.html"
    context_object_name = "changes"
    paginate_by = 25
    permission_required = ("service_desk.view_change",)

    def get_queryset(self):
        queryset = ChangeSelector.with_related(
            get_change_queryset(self.request.user)
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = ChangeSelector.search(queryset, search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = ChangeSelector.scoped_summary(
            get_change_queryset(self.request.user)
        )
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["status_choices"] = Change.STATUS_CHOICES
        return context


class ChangeCreateView(
    ChangeCreatePermissionMixin,
    CreateView
):
    model = Change
    form_class = ChangeCreateForm
    template_name = "changes/create.html"
    permission_required = ("service_desk.add_change",)
    success_url = reverse_lazy("service_desk:change_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = ChangeService.create_change(
                self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, f"Change '{self.object.title}' created.")
        return redirect("service_desk:change_detail", pk=self.object.pk)


class ChangeDetailView(
    ChangeViewPermissionMixin,
    DetailView
):
    model = Change
    template_name = "changes/detail.html"
    context_object_name = "change"
    permission_required = ("service_desk.view_change",)

    def get_queryset(self):
        return ChangeSelector.with_related(
            get_change_queryset(self.request.user)
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
        context["next_statuses"] = ChangeService.STATUS_FLOW.get(
            self.object.status, []
        )
        return context


class ChangeSubmitView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.submit_change(change, user=request.user)
            messages.success(request, "Change submitted for assessment.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeAssessView(ChangeChangePermissionMixin, View):
    def get(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        return render(
            request,
            "changes/assess.html",
            {"change": change, "form": ChangeAssessmentForm()},
        )

    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        form = ChangeAssessmentForm(request.POST)

        if not form.is_valid():
            return render(
                request, "changes/assess.html", {"change": change, "form": form}
            )

        try:
            ChangeService.assess_change(
                change,
                request.user,
                impact=form.cleaned_data["impact"],
                urgency=form.cleaned_data["urgency"],
            )
            messages.success(request, "Change assessed.")
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return render(
                request, "changes/assess.html", {"change": change, "form": form}
            )

        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeApproveView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.approve_change(
                change, request.user, comment=request.POST.get("comment", "")
            )
            messages.success(request, "Change approved.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeRejectView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.reject_change(
                change, request.user, comment=request.POST.get("comment", "")
            )
            messages.success(request, "Change rejected.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeScheduleView(ChangeChangePermissionMixin, View):
    def get(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        return render(
            request,
            "changes/schedule.html",
            {"change": change, "form": ChangeScheduleForm()},
        )

    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        form = ChangeScheduleForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "changes/schedule.html",
                {"change": change, "form": form},
            )

        try:
            ChangeService.schedule_change(
                change,
                request.user,
                start=form.cleaned_data["scheduled_start"],
                end=form.cleaned_data["scheduled_end"],
            )
            messages.success(request, "Change scheduled.")
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return render(
                request,
                "changes/schedule.html",
                {"change": change, "form": form},
            )

        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeAssignView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        technician = get_object_or_404(
            User, pk=request.POST.get("technician_id"), is_active=True
        )
        try:
            ChangeService.assign_change(change, technician, user=request.user)
            messages.success(
                request, f"Change assigned to {technician.get_username()}."
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeStartImplementationView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.start_implementation(change, user=request.user)
            messages.success(request, "Implementation started.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeRequestValidationView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.request_validation(change, user=request.user)
            messages.success(request, "Change moved to validation.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeCompleteView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.complete_change(change, user=request.user)
            messages.success(request, "Change completed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeFailView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.fail_change(
                change, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, "Change marked as failed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeRollbackView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.rollback_change(
                change, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, "Change rolled back.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)


class ChangeCommentView(ChangeChangePermissionMixin, View):
    def post(self, request, pk):
        change = get_object_or_404(get_change_queryset(request.user), pk=pk)
        try:
            ChangeService.add_comment(
                change, request.POST.get("comment", ""), user=request.user
            )
            messages.success(request, "Comment added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:change_detail", pk=change.pk)
