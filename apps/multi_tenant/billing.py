"""Bridge multi-tenant companies to billing subscriptions."""

from __future__ import annotations

from apps.billing.services import BillingService
from apps.service_desk.models import Company


def attach_default_plan(company: Company, plan_code: str = "starter", seats: int = 5):
    BillingService.seed_plans()
    return BillingService.subscribe(company, plan_code, seats=seats, trial_days=14)
