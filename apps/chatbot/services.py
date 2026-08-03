"""Self-service chatbot intents built on the AI copilot + portal services."""

from __future__ import annotations

import re

from apps.ai_engine.agents.copilot import CopilotAgent
from apps.customer_portal.services import PortalService
from apps.service_desk.services.knowledge_service import KnowledgeService


class ChatbotService:
    INTENT_PATTERNS = [
        ("create_ticket", re.compile(r"\b(create|open|raise|submit)\b.*\b(ticket|request|incident)\b", re.I)),
        ("status", re.compile(r"\b(status|update)\b.*\b(ticket|request)\b", re.I)),
        ("password", re.compile(r"\b(password|reset|locked out|mfa)\b", re.I)),
        ("knowledge", re.compile(r"\b(how (do|to)|help|guide|article)\b", re.I)),
    ]

    @classmethod
    def detect_intent(cls, message: str) -> str:
        for name, pattern in cls.INTENT_PATTERNS:
            if pattern.search(message or ""):
                return name
        return "general"

    @classmethod
    def handle(cls, *, user, company, message: str) -> dict:
        intent = cls.detect_intent(message)
        if intent == "create_ticket":
            ticket = PortalService.create_request(
                user,
                company,
                title=message[:240],
                description=message,
            )
            return {
                "intent": intent,
                "reply": f"I created request {ticket.ticket_number} for you.",
                "ticket_id": ticket.pk,
                "ticket_number": ticket.ticket_number,
            }
        if intent == "password":
            articles = list(
                KnowledgeService.search("password", company=company)[:3]
            )
            links = ", ".join(a.title for a in articles) or "the help center"
            return {
                "intent": intent,
                "reply": (
                    "For password issues, try the self-service reset first. "
                    f"Related articles: {links}."
                ),
                "articles": [{"title": a.title, "slug": a.slug} for a in articles],
            }
        if intent == "knowledge":
            articles = list(KnowledgeService.search(message, company=company)[:5])
            if not articles:
                return {
                    "intent": intent,
                    "reply": "I could not find matching articles. Try rephrasing or open a ticket.",
                    "articles": [],
                }
            return {
                "intent": intent,
                "reply": "Here are articles that may help:\n"
                + "\n".join(f"- {a.title}" for a in articles),
                "articles": [{"title": a.title, "slug": a.slug} for a in articles],
            }
        # general → copilot
        result = CopilotAgent(provider_name="local").reply(
            user=user, message=message, company=company
        )
        return {
            "intent": "general",
            "reply": result["answer"],
            "classification": result.get("classification"),
            "articles": result.get("articles") or [],
            "conversation_id": result.get("conversation_id"),
        }
