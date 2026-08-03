from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.vendor_management.models import Vendor, VendorContract


class VendorService:
    @staticmethod
    def create_vendor(company, *, name: str, code: str = "", **kwargs) -> Vendor:
        code = code or slugify(name)[:60]
        return Vendor.objects.create(company=company, name=name, code=code, **kwargs)

    @staticmethod
    def search(company, query: str = ""):
        qs = Vendor.objects.filter(company=company, is_active=True)
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(code__icontains=query)
                | Q(support_email__icontains=query)
            )
        return qs

    @staticmethod
    def expiring_contracts(company, within_days: int = 60):
        today = timezone.localdate()
        until = today + timezone.timedelta(days=within_days)
        return VendorContract.objects.filter(
            vendor__company=company,
            status=VendorContract.Status.ACTIVE,
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=until,
        ).select_related("vendor")
