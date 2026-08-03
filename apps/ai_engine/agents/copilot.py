"""Service desk AI copilot."""

from __future__ import annotations

import logging
import time

from apps.ai_engine.models import AIConversation, AIMessage, AIRequestLog
from apps.ai_engine.providers.claude_provider import ClaudeProvider
from apps.ai_engine.providers.ollama_provider import OllamaProvider
from apps.ai_engine.providers.openai_provider import OpenAIProvider
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class CopilotAgent:
    def __init__(self, provider_name: str = "local") -> None:
        self.provider_name = provider_name

    def _provider(self):
        if self.provider_name == "openai":
            return OpenAIProvider()
        if self.provider_name == "claude":
            return ClaudeProvider()
        if self.provider_name == "ollama":
            return OllamaProvider()
        return None

    def reply(
        self,
        *,
        user,
        message: str,
        company=None,
        ticket=None,
        conversation: AIConversation | None = None,
    ) -> dict:
        started = time.monotonic()
        if conversation is None:
            conversation = AIConversation.objects.create(
                user=user,
                company=company,
                ticket=ticket,
                title=(message[:80] or "Assistant chat"),
            )
        AIMessage.objects.create(
            conversation=conversation, role=AIMessage.Role.USER, content=message
        )

        classification = AIService.classify_text(message)
        articles = []
        if company is not None:
            articles = list(KnowledgeService.search(message, company=company)[:3])

        local_answer = self._local_answer(message, classification, articles, ticket)
        provider_name = "local"
        answer = local_answer
        success = True
        error = ""
        provider = self._provider()
        if provider is not None:
            try:
                kb_context = "\n".join(f"- {a.title}: {a.summary or a.body[:200]}" for a in articles)
                prompt = (
                    f"User question:\n{message}\n\n"
                    f"Classification: {classification}\n\n"
                    f"Knowledge:\n{kb_context or 'None'}\n\n"
                    "Provide a concise IT support response."
                )
                answer = provider.complete(prompt)
                provider_name = provider.name
            except Exception as exc:  # noqa: BLE001
                logger.warning("llm_provider_failed: %s", exc)
                success = False
                error = str(exc)
                answer = local_answer

        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=answer,
            metadata={"classification": classification, "provider": provider_name},
        )
        latency = int((time.monotonic() - started) * 1000)
        AIRequestLog.objects.create(
            company=company,
            user=user,
            provider=provider_name,
            operation="copilot.reply",
            prompt=message,
            response=answer,
            latency_ms=latency,
            success=success or provider_name == "local",
            error_message=error,
            metadata={"classification": classification},
        )
        conversation.save(update_fields=["updated_at"])
        return {
            "conversation_id": conversation.pk,
            "answer": answer,
            "classification": classification,
            "articles": [{"id": a.pk, "title": a.title, "slug": a.slug} for a in articles],
            "provider": provider_name,
        }

    @staticmethod
    def _local_answer(message: str, classification: dict, articles, ticket) -> str:
        parts = [
            f"I classified this as category **{classification.get('category') or 'general'}** "
            f"with priority hint **{classification.get('priority_hint')}**.",
        ]
        if ticket is not None:
            parts.append(
                f"Related ticket {ticket.ticket_number}: {ticket.title}."
            )
        if articles:
            parts.append("Suggested knowledge articles:")
            for a in articles:
                parts.append(f"- {a.title}")
        else:
            parts.append(
                "No knowledge articles matched. Capture impact, urgency, and recent changes, "
                "then escalate to the appropriate queue if the user is blocked."
            )
        summary = classification.get("summary") or message[:240]
        parts.append(f"Summary: {summary}")
        return "\n".join(parts)
