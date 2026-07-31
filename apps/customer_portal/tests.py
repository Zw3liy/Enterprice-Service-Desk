from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.customer_portal.services import PortalService
from apps.service_desk.models import Company, Department, RequestType, Status

User = get_user_model()


class PortalServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PortalCo", slug="portal-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        self.user = User.objects.create_user(username="enduser", password="pass12345")
        self.status = Status.objects.create(
            company=self.company, name="New", code="new", rank=10
        )
        self.rt = RequestType.objects.create(
            department=self.dept, name="Access request", code="access"
        )

    def test_create_request_and_list(self):
        profile = PortalService.ensure_profile(self.user, self.company)
        self.assertEqual(profile.company_id, self.company.pk)
        ticket = PortalService.create_request(
            self.user,
            self.company,
            title="Need VPN access",
            description="New starter",
            request_type=self.rt,
        )
        self.assertEqual(ticket.channel, "portal")
        self.assertEqual(ticket.ticket_type, "service_request")
        mine = PortalService.my_tickets(self.user, self.company)
        self.assertEqual(mine.count(), 1)


class PortalUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PortalUI", slug="portal-ui")
        self.user = User.objects.create_user(username="portalui", password="pass12345")
        self.client = Client()
        self.client.login(username="portalui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()

    def test_home(self):
        res = self.client.get(reverse("portal:home"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Service Portal")