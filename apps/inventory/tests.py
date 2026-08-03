from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.inventory.models import StockMovement
from apps.inventory.services import InventoryService
from apps.service_desk.models import Company

User = get_user_model()


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="InvCo", slug="inv-co")
        self.user = User.objects.create_user(username="invuser", password="pass12345")
        self.wh = InventoryService.ensure_warehouse(self.company)
        self.item = InventoryService.upsert_item(
            self.company, sku="NIC-1G", name="1G Network Card", reorder_level=2
        )

    def test_receipt_issue_reorder(self):
        InventoryService.move(
            company=self.company,
            warehouse=self.wh,
            item=self.item,
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity=10,
            user=self.user,
        )
        self.assertEqual(InventoryService.on_hand(self.item), 10)
        InventoryService.move(
            company=self.company,
            warehouse=self.wh,
            item=self.item,
            movement_type=StockMovement.MovementType.ISSUE,
            quantity=9,
            user=self.user,
        )
        self.assertEqual(InventoryService.on_hand(self.item), 1)
        below = InventoryService.below_reorder(self.company)
        self.assertEqual(len(below), 1)
