"""
IM-01

Regression coverage for the Create Ticket / Ticket Detail template
defects found during the frontend audit:

- Create Ticket previously rendered a non-existent "category" field
  and omitted the real urgency/request_type/tags fields.
- Ticket Detail previously compared status/priority against
  uppercase literals that never match the model's lowercase choices,
  so badge coloring was always dead.
"""

from django.test import TestCase, Client

from django.contrib.auth.models import User

from apps.service_desk.models import Department, Ticket


class TicketCreateTemplateTests(TestCase):

    def setUp(self):

        self.client = Client()

        self.admin = User.objects.create_superuser(
            username="im01_admin",
            password="password123",
            email="im01_admin@test.com",
        )

    def test_create_form_renders_real_model_fields(self):

        self.client.login(
            username="im01_admin",
            password="password123",
        )

        response = self.client.get("/tickets/new/")

        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        self.assertIn('id="id_urgency"', content)
        self.assertIn('id="id_request_type"', content)
        self.assertIn('id="id_tags"', content)

    def test_create_form_does_not_render_nonexistent_category_field(self):

        self.client.login(
            username="im01_admin",
            password="password123",
        )

        response = self.client.get("/tickets/new/")

        content = response.content.decode()

        self.assertNotIn('id="id_category"', content)


class TicketDetailTemplateTests(TestCase):

    def setUp(self):

        self.client = Client()

        self.admin = User.objects.create_superuser(
            username="im01_admin2",
            password="password123",
            email="im01_admin2@test.com",
        )

        self.department = Department.objects.create(
            name="IM-01 Department",
        )

    def test_open_status_badge_uses_warning_style(self):

        ticket = Ticket.objects.create(
            title="Open ticket",
            description="Status badge check",
            status="open",
            priority="urgent",
            created_by=self.admin,
            department=self.department,
        )

        self.client.login(
            username="im01_admin2",
            password="password123",
        )

        response = self.client.get(f"/tickets/{ticket.pk}/")

        content = response.content.decode()

        self.assertIn("bg-warning", content)
        self.assertIn("bg-danger", content)

    def test_resolved_status_badge_uses_success_style(self):

        ticket = Ticket.objects.create(
            title="Resolved ticket",
            description="Status badge check",
            status="resolved",
            priority="low",
            created_by=self.admin,
            department=self.department,
        )

        self.client.login(
            username="im01_admin2",
            password="password123",
        )

        response = self.client.get(f"/tickets/{ticket.pk}/")

        content = response.content.decode()

        self.assertIn("bg-success", content)
