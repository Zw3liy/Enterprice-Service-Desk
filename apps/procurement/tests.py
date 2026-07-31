from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.inventory.services import InventoryService
from apps.procurement.models import PurchaseOrder, PurchaseRequest
from apps.procurement.services import ProcurementService
from apps.service_desk.models import Company
from apps.vendor_management.services import VendorService

User = get_user_model()


class ProcurementServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="ProcCo", slug="proc-co")
        self.user = User.objects.create_user(
            username="buyer", password="pass12345", is_staff=True
        )
        self.vendor = VendorService.create_vendor(self.company, name="SupplyCo")

    def test_pr_to_po_receive(self):
        pr = ProcurementService.create_request(
            self.company,
            title="Laptops",
            requester=self.user,
            lines=[
                {
                    "description": "Laptop 14in",
                    "quantity": 2,
                    "unit_price": "15000.00",
                    "sku": "LPT-14",
                }
            ],
        )
        self.assertEqual(pr.total_estimate, Decimal("30000.00"))
        ProcurementService.submit(pr, actor=self.user)
        ProcurementService.decide(pr, approved=True, actor=self.user)
        po = ProcurementService.create_po_from_request(
            pr, vendor=self.vendor, user=self.user
        )
        self.assertTrue(po.number.startswith("PO-"))
        ProcurementService.send_po(po, actor=self.user)
        ProcurementService.receive_po(po, actor=self.user)
        po.refresh_from_db()
        self.assertEqual(po.state, PurchaseOrder.State.RECEIVED)
        item = self.company.stock_items.get(sku="LPT-14")
        self.assertEqual(InventoryService.on_hand(item), 2)
