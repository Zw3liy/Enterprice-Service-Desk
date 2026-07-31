from django.test import TestCase
from django.utils import timezone

from apps.service_desk.models import Asset, Company
from apps.warranty.models import WarrantyRecord
from apps.warranty.services import WarrantyService


class WarrantyServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="WarCo", slug="war-co")
        self.asset = Asset.objects.create(
            company=self.company, name="Switch", asset_tag="SW-1"
        )

    def test_active_and_expiring(self):
        today = timezone.localdate()
        WarrantyService.create_for_asset(
            self.asset,
            start_date=today - timezone.timedelta(days=300),
            end_date=today + timezone.timedelta(days=20),
            provider_name="OEM Care",
        )
        self.assertEqual(WarrantyService.active_for_asset(self.asset).count(), 1)
        self.assertEqual(WarrantyService.expiring(self.company, within_days=30).count(), 1)
        # expire
        WarrantyRecord.objects.all().update(end_date=today - timezone.timedelta(days=1))
        n = WarrantyService.refresh_expired(self.company)
        self.assertEqual(n, 1)
