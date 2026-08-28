"""
apps/service_desk/release_views.py

Release Management.

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

from .forms.release_forms import ReleaseCreateForm, ReleaseScheduleForm
from .models import Change, Release
from .security.mixins import (
    ReleaseChangePermissionMixin,
    ReleaseCreatePermissionMixin,
    ReleaseViewPermissionMixin,
)
from .security.policies import get_change_queryset, get_release_queryset
from .selectors.release_selector import ReleaseSelector
from .services.release_service import ReleaseService

User = get_user_model()


class ReleaseListView(ReleaseViewPermissionMixin, ListView):
    model = Release
    template_name = "releases/list.html"
    context_object_name = "releases"
    paginate_by = 25
    permission_required = ("service_desk.view_release",)

    def get_queryset(self):
        queryset = ReleaseSelector.with_related(
            get_release_queryset(self.request.user)
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = ReleaseSelector.search(queryset, search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = ReleaseSelector.scoped_summary(
            get_release_queryset(self.request.user)
        )
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["status_choices"] = Release.STATUS_CHOICES
        return context


class ReleaseCreateView(ReleaseCreatePermissionMixin, CreateView):
    model = Release
    form_class = ReleaseCreateForm
    template_name = "releases/create.html"
    permission_required = ("service_desk.add_release",)
    success_url = reverse_lazy("service_desk:release_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = ReleaseService.create_release(
                self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, f"Release '{self.object}' created.")
        return redirect("service_desk:release_detail", pk=self.object.pk)


class ReleaseDetailView(ReleaseViewPermissionMixin, DetailView):
    model = Release
    template_name = "releases/detail.html"
    context_object_name = "release"
    permission_required = ("service_desk.view_release",)

    def get_queryset(self):
        return ReleaseSelector.with_related(
            get_release_queryset(self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approvals"] = self.object.approvals.select_related("actor")
        context["history"] = self.object.history.select_related(
            "performed_by"
        )
        context["linked_changes"] = self.object.changes.all()

        eligible_changes = get_change_queryset(self.request.user).filter(
            status__in=Release.CHANGE_ELIGIBLE_STATUSES
        ).exclude(pk__in=self.object.changes.values("pk"))
        context["eligible_changes"] = eligible_changes

        context["available_owners"] = User.objects.filter(
            groups__name__in=["Technician", "Manager"],
            is_active=True,
        ).distinct().order_by("username")

        context["next_statuses"] = ReleaseService.STATUS_FLOW.get(
            self.object.status, []
        )
        return context


class ReleaseApproveView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.approve_release(
                release, request.user, comment=request.POST.get("comment", "")
            )
            messages.success(request, "Release approved.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseScheduleView(ReleaseChangePermissionMixin, View):
    def get(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        return render(
            request,
            "releases/schedule.html",
            {"release": release, "form": ReleaseScheduleForm()},
        )

    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        form = ReleaseScheduleForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "releases/schedule.html",
                {"release": release, "form": form},
            )

        try:
            ReleaseService.schedule_release(
                release,
                request.user,
                start=form.cleaned_data["scheduled_start"],
                end=form.cleaned_data["scheduled_end"],
            )
            messages.success(request, "Release scheduled.")
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return render(
                request,
                "releases/schedule.html",
                {"release": release, "form": form},
            )

        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseLinkChangeView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        change = get_object_or_404(
            get_change_queryset(request.user),
            pk=request.POST.get("change_id"),
        )

        try:
            ReleaseService.link_change(release, change, user=request.user)
            messages.success(request, f"Linked change '{change}'.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseUnlinkChangeView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk, change_pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        change = get_object_or_404(Change, pk=change_pk)

        ReleaseService.unlink_change(release, change, user=request.user)
        messages.success(request, f"Unlinked change '{change}'.")

        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseAssignOwnerView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        new_owner = get_object_or_404(
            User, pk=request.POST.get("owner_id"), is_active=True
        )

        try:
            ReleaseService.assign_owner(release, new_owner, user=request.user)
            messages.success(
                request, f"Release owner set to {new_owner.get_username()}."
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseStartDeploymentView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.start_deployment(release, user=request.user)
            messages.success(request, "Deployment started.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseRequestValidationView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.request_validation(release, user=request.user)
            messages.success(request, "Release moved to validation.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseCompleteView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.complete_release(
                release, user=request.user, outcome=request.POST.get("outcome", "")
            )
            messages.success(request, "Release completed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseFailView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.fail_release(
                release, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, "Release marked as failed.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseRollbackView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.rollback_release(
                release, request.user, reason=request.POST.get("reason", "")
            )
            messages.success(request, "Release rolled back.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)


class ReleaseCommentView(ReleaseChangePermissionMixin, View):
    def post(self, request, pk):
        release = get_object_or_404(get_release_queryset(request.user), pk=pk)
        try:
            ReleaseService.add_comment(
                release, request.POST.get("comment", ""), user=request.user
            )
            messages.success(request, "Comment added.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:release_detail", pk=release.pk)
