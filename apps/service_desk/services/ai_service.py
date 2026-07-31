"""Lightweight AI assistance (rule-based, pluggable to LLM providers)."""

from __future__ import annotations

import logging
import re
from typing import Optional

from django.db.models import Q

from apps.service_desk.models import Category, KnowledgeArticle, Priority, Ticket

logger = logging.getLogger(__name__)

# Keyword heuristics — replaced/extended by real LLM providers when configured.
PRIORITY_KEYWORDS = {
    "critical": [
        "outage",
        "down",
        "production",
        "sev1",
        "p1",
        "ransomware",
        "data breach",
        "cannot work",
        "entire company",
    ],
    "high": [
        "urgent",
        "asap",
        "blocked",
        "vip",
        "ceo",
        "security",
        "breach",
        "payroll",
    ],
    "medium": ["slow", "intermittent", "degraded", "error"],
    "low": ["question", "how do i", "request", "when possible", "low priority"],
}

CATEGORY_KEYWORDS = {
    "network": ["vpn", "wifi", "network", "firewall", "dns", "latency", "switch", "router"],
    "email": ["outlook", "email", "mailbox", "exchange", "o365", "teams"],
    "hardware": ["laptop", "desktop", "printer", "monitor", "keyboard", "dock"],
    "access": ["password", "locked", "mfa", "login", "permission", "access", "account"],
    "software": ["install", "license", "application", "crash", "update", "office"],
    "telephony": ["phone", "softphone", "call quality", "headset"],
}

SENTIMENT_NEG = {
    "angry",
    "furious",
    "unacceptable",
    "terrible",
    "worst",
    "immediately",
    "lawsuit",
    "escalate",
    "disappointed",
    "frustrated",
}
SENTIMENT_POS = {"thanks", "thank you", "appreciate", "great", "please", "kindly"}


class AIService:
    @classmethod
    def enrich_ticket(cls, ticket: Ticket) -> Ticket:
        text = f"{ticket.title}\n{ticket.description}".lower()
        ticket.ai_summary = cls.summarize(ticket.title, ticket.description)
        ticket.sentiment_score = cls.score_sentiment(text)
        suggestion = cls.suggest_category_code(text)
        if suggestion:
            ticket.ai_category_suggestion = suggestion
            if ticket.company_id and not ticket.category_id:
                cat = Category.objects.filter(
                    company=ticket.company, code__icontains=suggestion, is_active=True
                ).first()
                if cat is None:
                    cat = Category.objects.filter(
                        company=ticket.company, name__icontains=suggestion, is_active=True
                    ).first()
                if cat:
                    ticket.category = cat
        if ticket.company_id and not ticket.priority_id:
            prio = cls.suggest_priority(ticket.company, text)
            if prio:
                ticket.priority = prio
        ticket.save()
        logger.debug("ai_enrich ticket=%s sentiment=%s", ticket.pk, ticket.sentiment_score)
        return ticket

    @staticmethod
    def summarize(title: str, description: str, max_len: int = 280) -> str:
        body = (description or "").strip()
        if not body:
            return (title or "")[:max_len]
        # First sentence / truncated abstract
        parts = re.split(r"(?<=[.!?])\s+", body)
        summary = parts[0] if parts else body
        if len(summary) > max_len:
            summary = summary[: max_len - 1].rsplit(" ", 1)[0] + "…"
        return summary

    @staticmethod
    def score_sentiment(text: str) -> float:
        tokens = set(re.findall(r"[a-z']+", text.lower()))
        score = 0.0
        for t in tokens:
            if t in SENTIMENT_NEG:
                score -= 0.15
            if t in SENTIMENT_POS:
                score += 0.1
        return max(-1.0, min(1.0, score))

    @staticmethod
    def suggest_category_code(text: str) -> str:
        best = ""
        best_hits = 0
        for code, words in CATEGORY_KEYWORDS.items():
            hits = sum(1 for w in words if w in text)
            if hits > best_hits:
                best_hits = hits
                best = code
        return best

    @staticmethod
    def suggest_priority(company, text: str) -> Optional[Priority]:
        chosen_code = "medium"
        for code, words in PRIORITY_KEYWORDS.items():
            if any(w in text for w in words):
                chosen_code = code
                break
        # Map common codes
        mapping = {
            "critical": ["critical", "p1", "urgent"],
            "high": ["high", "p2"],
            "medium": ["medium", "p3", "normal"],
            "low": ["low", "p4"],
        }
        codes = mapping.get(chosen_code, [chosen_code])
        for code in codes:
            p = Priority.objects.filter(company=company, code__iexact=code, is_active=True).first()
            if p:
                return p
        return (
            Priority.objects.filter(company=company, is_active=True)
            .order_by("rank")
            .first()
        )

    @classmethod
    def recommend_articles(cls, ticket: Ticket, limit: int = 5) -> list[KnowledgeArticle]:
        if not ticket.company_id:
            return []
        tokens = re.findall(r"[a-z0-9]{4,}", f"{ticket.title} {ticket.description}".lower())
        if not tokens:
            return list(
                KnowledgeArticle.objects.filter(
                    company=ticket.company, is_published=True
                )[:limit]
            )
        q = Q()
        for token in tokens[:12]:
            q |= Q(title__icontains=token) | Q(body__icontains=token) | Q(summary__icontains=token)
        return list(
            KnowledgeArticle.objects.filter(company=ticket.company, is_published=True)
            .filter(q)
            .distinct()[:limit]
        )

    @classmethod
    def classify_text(cls, text: str) -> dict:
        lowered = text.lower()
        return {
            "category": cls.suggest_category_code(lowered),
            "sentiment": cls.score_sentiment(lowered),
            "summary": cls.summarize("", text),
            "priority_hint": next(
                (
                    code
                    for code, words in PRIORITY_KEYWORDS.items()
                    if any(w in lowered for w in words)
                ),
                "medium",
            ),
        }
