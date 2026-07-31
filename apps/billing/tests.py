from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.billing.models import Invoice, Plan, Subscription
from apps.billing.services import BillingService
from apps.service_desk.models import Company

User = get_user_model()


class BillingServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="BillCo", slug="bill-co")
        self.user = User.objects.create_user(
            username="billadmin", password="pass12345", is_staff=True
        )

    def test_seed_subscribe_invoice(self):
        n = BillingService.seed_plans()
        self.assertGreaterEqual(n, 1)
        sub = BillingService.subscribe(
            self.company, "professional", seats=5, actor=self.user
        )
        self.assertEqual(sub.plan.code, "professional")
        self.assertTrue(sub.is_usable)
        limits = BillingService.check_limits(self.company)
        self.assertIn("usage", limits)
        invoice = BillingService.generate_invoice(self.company, actor=self.user)
        self.assertEqual(invoice.status, Invoice.Status.OPEN)
        self.assertGreater(invoice.total, Decimal("0"))
        BillingService.mark_paid(invoice, actor=self.user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)


class BillingUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="BillUI", slug="bill-ui")
        self.user = User.objects.create_user(
            username="billui", password="pass12345", is_staff=True
        )
        BillingService.seed_plans()
        self.client = Client()
        self.client.login(username="billui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_dashboard(self):
        res = self.client.get(reverse("billing:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Professional")