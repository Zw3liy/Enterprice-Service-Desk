from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.warranty.models import WarrantyRecord


class WarrantyService:
    @staticmethod
    def create_for_asset(asset, *, start_date, end_date, vendor=None, **kwargs) -> WarrantyRecord:
        return WarrantyRecord.objects.create(
            company=asset.company,
            asset=asset,
            vendor=vendor,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

    @staticmethod
    def active_for_asset(asset):
        today = timezone.localdate()
        return WarrantyRecord.objects.filter(
            asset=asset,
            status=WarrantyRecord.Status.ACTIVE,
            start_date__lte=today,
            end_date__gte=today,
        )

    @staticmethod
    def expiring(company, within_days: int = 60):
        today = timezone.localdate()
        until = today + timezone.timedelta(days=within_days)
        return WarrantyRecord.objects.filter(
            company=company,
            status=WarrantyRecord.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=until,
        ).select_related("asset", "vendor")

    @staticmethod
    def refresh_expired(company=None) -> int:
        today = timezone.localdate()
        qs = WarrantyRecord.objects.filter(
            status=WarrantyRecord.Status.ACTIVE, end_date__lt=today
        )
        if company is not None:
            qs = qs.filter(company=company)
        return qs.update(status=WarrantyRecord.Status.EXPIRED)
