from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chatbot.services import ChatbotService
from apps.service_desk.models import Company, Department, Status

User = get_user_model()


class ChatbotServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="BotCo", slug="bot-co")
        Department.objects.create(company=self.company, name="IT", code="it")
        Status.objects.create(company=self.company, name="New", code="new", rank=10)
        self.user = User.objects.create_user(username="botuser", password="pass12345")

    def test_create_ticket_intent(self):
        result = ChatbotService.handle(
            user=self.user,
            company=self.company,
            message="Please create a ticket for broken laptop screen",
        )
        self.assertEqual(result["intent"], "create_ticket")
        self.assertIn("ticket_number", result)

    def test_general_intent(self):
        result = ChatbotService.handle(
            user=self.user,
            company=self.company,
            message="What is the weather in the data center?",
        )
        self.assertEqual(result["intent"], "general")
        self.assertIn("reply", result)
