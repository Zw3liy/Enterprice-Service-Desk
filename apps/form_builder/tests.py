from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.form_builder.services import FormBuilderService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class FormBuilderTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="FormCo", slug="form-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(username="formuser", password="pass12345")

    def test_create_and_submit(self):
        form = FormBuilderService.create_form(
            self.company,
            name="Hardware request",
            schema=[
                {"name": "item", "label": "Item", "type": "text", "required": True},
                {
                    "name": "urgency",
                    "label": "Urgency",
                    "type": "dropdown",
                    "required": True,
                    "options": ["low", "high"],
                },
            ],
        )
        with self.assertRaises(ValidationError):
            FormBuilderService.submit(form, {"item": "Laptop"}, user=self.user)
        sub = FormBuilderService.submit(
            form,
            {"item": "Laptop", "urgency": "high"},
            user=self.user,
            title="Need laptop",
        )
        self.assertIsNotNone(sub.ticket_id)
        self.assertEqual(sub.values["item"], "Laptop")
