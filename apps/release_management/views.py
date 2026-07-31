from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.release_management.models import Release, ReleaseTask
from apps.release_management.serializers import (
    ReleaseCreateSerializer,
    ReleaseSerializer,
    ReleaseTaskSerializer,
)
from apps.release_management.services import ReleaseService
from apps.service_desk.tenancy import get_active_company, require_company


@login_required
def release_list(request):
    company = get_active_company(request)
    qs = Release.objects.all()
    if company:
        qs = qs.filter(company=company)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/releases/list.html",
        {"title": "Releases", "page": page},
    )


@login_required
def release_detail(request, pk: int):
    release = get_object_or_404(Release.objects.prefetch_related("tasks", "changes"), pk=pk)
    return render(
        request,
        "itil/releases/detail.html",
        {
            "title": release.version,
            "release": release,
            "state_choices": Release.State.choices,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def release_create(request):
    company = require_company(request)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        version = (request.POST.get("version") or "").strip()
        if name and version:
            release = ReleaseService.create_release(
                company,
                name=name,
                version=version,
                description=request.POST.get("description") or "",
                manager=request.user,
                actor=request.user,
            )
            messages.success(request, f"Release {release.version} created.")
            return redirect("releases:detail", pk=release.pk)
        messages.error(request, "Name and version are required.")
    return render(request, "itil/releases/create.html", {"title": "New release"})


@login_required
@require_POST
def release_transition(request, pk: int):
    release = get_object_or_404(Release, pk=pk)
    state = request.POST.get("state") or release.state
    ReleaseService.transition(release, state, actor=request.user)
    messages.success(request, f"Release moved to {state}.")
    return redirect("releases:detail", pk=pk)


class ReleaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReleaseSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Release.objects.prefetch_related("tasks", "changes")
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = ReleaseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        release = ReleaseService.create_release(
            company,
            name=ser.validated_data["name"],
            version=ser.validated_data["version"],
            description=ser.validated_data.get("description") or "",
            planned_start=ser.validated_data.get("planned_start"),
            planned_end=ser.validated_data.get("planned_end"),
            change_ids=ser.validated_data.get("change_ids") or [],
            manager=request.user,
            actor=request.user,
        )
        return Response(ReleaseSerializer(release).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        release = self.get_object()
        state = request.data.get("state")
        if state not in dict(Release.State.choices):
            return Response({"detail": "Invalid state"}, status=400)
        ReleaseService.transition(release, state, actor=request.user)
        return Response(ReleaseSerializer(release).data)

    @action(detail=True, methods=["post"], url_path=r"tasks/(?P<task_id>[^/.]+)/complete")
    def complete_task(self, request, pk=None, task_id=None):
        release = self.get_object()
        task = get_object_or_404(ReleaseTask, pk=task_id, release=release)
        ReleaseService.complete_task(task, actor=request.user)
        return Response(ReleaseTaskSerializer(task).data)