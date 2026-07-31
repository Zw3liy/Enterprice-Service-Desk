from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.field_service.models import WorkOrder
from apps.field_service.services import FieldService
from apps.service_desk.models import Company, Department, Status
from apps.service_desk.services.ticket_service import TicketService

User = get_user_model()


class FieldServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="FieldCo", slug="field-co")
        self.dept = Department.objects.create(
            company=self.company, name="IT", code="it"
        )
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.tech = User.objects.create_user(
            username="tech1", password="pass12345", is_staff=True
        )
        self.ticket = TicketService.create_ticket(
            title="Replace access point",
            company=self.company,
            department=self.dept,
            actor=self.tech,
            run_ai=False,
        )

    def test_lifecycle(self):
        wo = FieldService.create_work_order(
            self.ticket,
            location="Building B floor 3",
            technician=self.tech,
            actor=self.tech,
        )
        self.assertTrue(wo.number.startswith("WO-"))
        FieldService.dispatch(wo, actor=self.tech)
        wo.refresh_from_db()
        self.assertEqual(wo.state, WorkOrder.State.DISPATCHED)
        FieldService.check_in(wo, actor=self.tech)
        FieldService.complete(wo, notes="AP replaced", actor=self.tech)
        wo.refresh_from_db()
        self.assertEqual(wo.state, WorkOrder.State.COMPLETED)
