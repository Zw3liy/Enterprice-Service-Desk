from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.ai_engine.agents.copilot import CopilotAgent
from apps.service_desk.models import Company

User = get_user_model()


class CopilotTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="AI Co", slug="ai-co")
        self.user = User.objects.create_user(username="aiuser", password="pass12345")

    def test_local_reply(self):
        result = CopilotAgent(provider_name="local").reply(
            user=self.user,
            message="VPN is down for the whole office",
            company=self.company,
        )
        self.assertIn("answer", result)
        self.assertTrue(result["conversation_id"])
        self.assertEqual(result["classification"]["category"], "network")


class AIUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aiui", password="pass12345")
        self.client = Client()
        self.client.login(username="aiui", password="pass12345")

    def test_assistant_page(self):
        res = self.client.get(reverse("ai_engine:assistant"))
        self.assertEqual(res.status_code, 200)
