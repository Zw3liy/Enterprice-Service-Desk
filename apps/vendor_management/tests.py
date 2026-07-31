from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.service_desk.models import Company
from apps.vendor_management.models import VendorContract
from apps.vendor_management.services import VendorService

User = get_user_model()


class VendorServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="VenCo", slug="ven-co")

    def test_create_and_expiring(self):
        vendor = VendorService.create_vendor(
            self.company, name="Acme Cloud", support_email="ops@acme.example"
        )
        VendorContract.objects.create(
            vendor=vendor,
            title="Support retainer",
            status=VendorContract.Status.ACTIVE,
            start_date=timezone.localdate() - timezone.timedelta(days=300),
            end_date=timezone.localdate() + timezone.timedelta(days=20),
        )
        exp = VendorService.expiring_contracts(self.company, within_days=30)
        self.assertEqual(exp.count(), 1)


class VendorUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="VenUI", slug="ven-ui")
        self.user = User.objects.create_user(
            username="venui", password="pass12345", is_staff=True
        )
        VendorService.create_vendor(self.company, name="NetGear SA")
        self.client = Client()
        self.client.login(username="venui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_list(self):
        res = self.client.get(reverse("vendors:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "NetGear SA")
