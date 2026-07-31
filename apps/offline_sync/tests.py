from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.offline_sync.models import OfflineMutation
from apps.offline_sync.services import OfflineSyncService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class OfflineSyncTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="OffCo", slug="off-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(username="mobile1", password="pass12345")

    def test_pull_and_push_create(self):
        pulled = OfflineSyncService.pull(self.company, self.user, "device-a")
        self.assertIn("cursor_token", pulled)
        results = OfflineSyncService.push(
            self.company,
            self.user,
            "device-a",
            [
                {
                    "client_mutation_id": "m1",
                    "entity_type": "ticket",
                    "operation": "create",
                    "payload": {"title": "Offline created", "description": "from field"},
                }
            ],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].state, OfflineMutation.State.APPLIED)
        self.assertIn("ticket_id", results[0].result)
