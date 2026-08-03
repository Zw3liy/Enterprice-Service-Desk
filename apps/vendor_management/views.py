from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.service_desk.tenancy import get_active_company, require_company
from apps.vendor_management.models import Vendor, VendorContract
from apps.vendor_management.serializers import VendorContractSerializer, VendorSerializer
from apps.vendor_management.services import VendorService


@login_required
def vendor_list(request):
    company = get_active_company(request)
    q = request.GET.get("q", "")
    qs = VendorService.search(company, q) if company else Vendor.objects.none()
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    expiring = VendorService.expiring_contracts(company) if company else []
    return render(
        request,
        "itil/vendors/list.html",
        {"title": "Vendors", "page": page, "q": q, "expiring": expiring},
    )


@login_required
def vendor_detail(request, pk: int):
    vendor = get_object_or_404(Vendor.objects.prefetch_related("contracts"), pk=pk)
    return render(
        request,
        "itil/vendors/detail.html",
        {"title": vendor.name, "vendor": vendor},
    )


@login_required
@require_http_methods(["GET", "POST"])
def vendor_create(request):
    company = require_company(request)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            vendor = VendorService.create_vendor(
                company,
                name=name,
                code=request.POST.get("code") or "",
                support_email=request.POST.get("support_email") or "",
                website=request.POST.get("website") or "",
                notes=request.POST.get("notes") or "",
            )
            messages.success(request, f"Vendor {vendor.name} created.")
            return redirect("vendors:detail", pk=vendor.pk)
        messages.error(request, "Name is required.")
    return render(request, "itil/vendors/create.html", {"title": "New vendor"})


class VendorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VendorSerializer
    search_fields = ("name", "code", "support_email")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Vendor.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class VendorContractViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VendorContractSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = VendorContract.objects.select_related("vendor")
        if company:
            qs = qs.filter(vendor__company=company)
        return qs
