from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.marketplace.models import InstalledApp
from apps.marketplace.services import MarketplaceService
from apps.service_desk.models import Company, WebhookEndpoint

User = get_user_model()


class MarketplaceServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="MktCo", slug="mkt-co")
        self.user = User.objects.create_user(
            username="mktadmin", password="pass12345", is_staff=True
        )

    def test_seed_and_install(self):
        n = MarketplaceService.seed_catalog()
        self.assertGreaterEqual(n, 1)
        install = MarketplaceService.install(
            self.company,
            "slack-notify",
            config={"webhook_url": "https://hooks.example/slack", "channel": "#it"},
            user=self.user,
        )
        self.assertEqual(install.state, InstalledApp.State.INSTALLED)
        self.assertTrue(
            WebhookEndpoint.objects.filter(
                company=self.company, url="https://hooks.example/slack"
            ).exists()
        )
