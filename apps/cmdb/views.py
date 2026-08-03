from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cmdb.models import CIClass, CIRelationship, ConfigurationItem, DiscoveryResult
from apps.cmdb.serializers import (
    CIClassSerializer,
    CIRelationshipSerializer,
    ConfigurationItemSerializer,
    DiscoveryIngestSerializer,
    DiscoveryResultSerializer,
)
from apps.cmdb.services import CMDBService
from apps.service_desk.tenancy import get_active_company, require_company


@login_required
def ci_list(request):
    company = get_active_company(request)
    q = request.GET.get("q", "")
    qs = (
        CMDBService.search(company, q)
        if company
        else ConfigurationItem.objects.none()
    )
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "itil/cmdb/list.html",
        {"title": "Configuration Items", "page": page, "q": q},
    )


@login_required
def ci_detail(request, pk: int):
    ci = get_object_or_404(
        ConfigurationItem.objects.select_related("ci_class", "asset", "company"),
        pk=pk,
    )
    tree = CMDBService.impact_tree(ci)
    return render(
        request,
        "itil/cmdb/detail.html",
        {
            "title": ci.ci_id,
            "ci": ci,
            "tree": tree,
            "outbound": ci.outbound.select_related("target"),
            "inbound": ci.inbound.select_related("source"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def ci_create(request):
    company = require_company(request)
    CMDBService.ensure_default_classes(company)
    classes = CIClass.objects.filter(company=company)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            ci = CMDBService.upsert_ci(
                company,
                name=name,
                ci_id=request.POST.get("ci_id") or "",
                ci_class_code=request.POST.get("ci_class") or "server",
                environment=request.POST.get("environment") or "production",
                criticality=int(request.POST.get("criticality") or 3),
            )
            messages.success(request, f"CI {ci.ci_id} saved.")
            return redirect("cmdb_app:detail", pk=ci.pk)
        messages.error(request, "Name is required.")
    return render(
        request,
        "itil/cmdb/create.html",
        {"title": "New CI", "classes": classes},
    )


class ConfigurationItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfigurationItemSerializer
    search_fields = ("name", "ci_id", "environment")
    filterset_fields = ("company", "environment", "is_active", "ci_class")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ConfigurationItem.objects.select_related("ci_class", "asset", "company")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = get_active_company(self.request)
        serializer.save(company=company)

    @action(detail=True, methods=["get"])
    def impact(self, request, pk=None):
        ci = self.get_object()
        return Response(CMDBService.impact_tree(ci))

    @action(detail=True, methods=["post"])
    def relate(self, request, pk=None):
        ci = self.get_object()
        target_id = request.data.get("target_id")
        relation_type = request.data.get("relation_type") or "related"
        target = get_object_or_404(ConfigurationItem, pk=target_id)
        rel = CMDBService.link(ci, target, relation_type=relation_type)
        return Response(CIRelationshipSerializer(rel).data, status=status.HTTP_201_CREATED)


class CIClassViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CIClassSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = CIClass.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=get_active_company(self.request))


class DiscoveryIngestAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = DiscoveryIngestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        payload = {**ser.validated_data.pop("extra", {}), **ser.validated_data}
        result = CMDBService.ingest_discovery(company, payload, source="api")
        return Response(
            DiscoveryResultSerializer(result).data, status=status.HTTP_201_CREATED
        )

    def get(self, request):
        company = get_active_company(request)
        qs = DiscoveryResult.objects.all()
        if company:
            qs = qs.filter(company=company)
        return Response(DiscoveryResultSerializer(qs[:100], many=True).data)