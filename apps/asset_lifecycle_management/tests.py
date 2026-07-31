from django.test import TestCase

from apps.asset_lifecycle_management.services import AssetLifecycleService
from apps.service_desk.models import Asset, Company


class AssetLifecycleTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="LifeCo", slug="life-co")

    def test_happy_path(self):
        asset = AssetLifecycleService.procure(
            self.company, name="Laptop", asset_tag="LPT-100", asset_type=Asset.AssetType.COMPUTER
        )
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.ORDERED)
        AssetLifecycleService.receive(asset)
        asset.refresh_from_db()
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.IN_STOCK)
        AssetLifecycleService.assign_to_use(asset)
        asset.refresh_from_db()
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.IN_USE)
        AssetLifecycleService.retire(asset)
        asset.refresh_from_db()
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.RETIRED)
