from django.test import TestCase

from apps.event_engine.models import DomainEvent
from apps.event_engine.services import EventBus
from apps.service_desk.models import Company


class EventBusTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="EvtCo", slug="evt-co")
        self.seen = []

        def handler(**kwargs):
            self.seen.append(kwargs["event_type"])

        EventBus.subscribe("ticket.demo", handler)

    def test_publish_persists_and_notifies(self):
        event = EventBus.publish(
            "ticket.demo",
            {"id": 1},
            company=self.company,
            aggregate_type="ticket",
            aggregate_id="1",
        )
        self.assertIsInstance(event, DomainEvent)
        self.assertIn("ticket.demo", self.seen)
        self.assertEqual(DomainEvent.objects.filter(event_type="ticket.demo").count(), 1)
