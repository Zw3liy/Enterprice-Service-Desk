from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.service_desk.models import Company, Department, Status
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class GraphQLAPITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="GqlCo", slug="gql-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(
            username="gqluser", password="pass12345", is_staff=True
        )
        self.ticket = TicketService.create_ticket(
            title="GraphQL ticket",
            company=self.company,
            actor=self.user,
            run_ai=False,
        )
        self.api = APIClient()
        token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        s = self.api.session
        s["company_id"] = self.company.pk
        s.save()

    def test_tickets_query(self):
        res = self.api.post(
            "/graphql/",
            {"query": "{ tickets { id ticketNumber title } }"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("data", res.json())
        self.assertTrue(res.json()["data"]["tickets"])

    def test_dashboard_query(self):
        res = self.api.post(
            "/graphql/",
            {"query": "{ dashboard { openTickets totalTickets } }"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("openTickets", res.json()["data"]["dashboard"])
