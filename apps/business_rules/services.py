from __future__ import annotations

import logging
from typing import Any

from django.utils.text import slugify

from apps.business_rules.models import BusinessRule
from apps.service_desk.services.automation_service import AutomationService

logger = logging.getLogger(__name__)


class BusinessRulesEngine:
    """Evaluates tenant business rules; reuses automation action executor semantics."""

    @staticmethod
    def create_rule(company, *, name: str, code: str = "", **kwargs) -> BusinessRule:
        return BusinessRule.objects.create(
            company=company,
            name=name,
            code=code or slugify(name)[:60],
            **kwargs,
        )

    @classmethod
    def evaluate(cls, company, scope: str, context: dict[str, Any]) -> list[str]:
        rules = BusinessRule.objects.filter(
            company=company, scope=scope, is_active=True
        ).order_by("priority", "id")
        applied = []
        for rule in rules:
            if not AutomationService._match(rule.conditions or {}, context):
                continue
            ticket = context.get("ticket")
            if ticket is not None:
                AutomationService._execute(rule.actions or [], ticket, context)
            applied.append(rule.name)
            logger.info("business_rule_applied rule=%s scope=%s", rule.code, scope)
            if rule.stop_on_match:
                break
        return applied
