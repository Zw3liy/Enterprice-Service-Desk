from django.test import TestCase
from unittest.mock import MagicMock, patch

from apps.service_desk.models import Company, WebhookEndpoint
from apps.webhooks.models import WebhookDelivery
from apps.webhooks.services import WebhookService


class WebhookServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="HookCo", slug="hook-co")
        self.endpoint = WebhookEndpoint.objects.create(
            company=self.company,
            name="Test sink",
            url="https://example.com/hooks",
            secret="s3cret",
            events=["ticket.created", "test.ping"],
            is_active=True,
        )

    @patch("apps.webhooks.services.urllib.request.urlopen")
    def test_dispatch_success(self, mock_urlopen):
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"ok":true}'
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        mock_urlopen.return_value = resp
        deliveries = WebhookService.dispatch(
            self.company, "ticket.created", {"id": 1}
        )
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].status, WebhookDelivery.Status.SUCCESS)
        self.assertEqual(deliveries[0].response_code, 200)