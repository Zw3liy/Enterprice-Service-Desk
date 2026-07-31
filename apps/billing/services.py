"""Billing application services."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import Invoice, Plan, Subscription, UsageRecord
from apps.billing.plans import DEFAULT_PLANS
from apps.billing.usage import current_period, snapshot_usage
from apps.service_desk.models import Company
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class BillingService:
    @staticmethod
    def seed_plans() -> int:
        count = 0
        for data in DEFAULT_PLANS:
            _, created = Plan.objects.update_or_create(
                code=data["code"], defaults=data
            )
            if created:
                count += 1
        return count

    @classmethod
    @transaction.atomic
    def subscribe(
        cls,
        company: Company,
        plan_code: str,
        *,
        seats: int = 1,
        trial_days: int = 14,
        billing_email: str = "",
        actor=None,
    ) -> Subscription:
        cls.seed_plans()
        plan = Plan.objects.get(code=plan_code, is_active=True)
        now = timezone.now()
        sub, created = Subscription.objects.update_or_create(
            company=company,
            defaults={
                "plan": plan,
                "status": Subscription.Status.TRIALING
                if trial_days > 0
                else Subscription.Status.ACTIVE,
                "seats": max(seats, 1),
                "billing_email": billing_email or company.primary_email,
                "trial_ends_at": now + timedelta(days=trial_days) if trial_days else None,
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
            },
        )
        AuditService.log(
            action="billing.subscribed",
            company=company,
            actor=actor,
            message=f"Subscribed to {plan.code}",
            object_type="subscription",
            object_id=str(sub.pk),
        )
        logger.info("subscribe company=%s plan=%s", company.slug, plan.code)
        return sub

    @classmethod
    def change_plan(cls, company: Company, plan_code: str, actor=None) -> Subscription:
        plan = Plan.objects.get(code=plan_code, is_active=True)
        sub = company.subscription
        sub.plan = plan
        sub.save(update_fields=["plan", "updated_at"])
        AuditService.log(
            action="billing.plan_changed",
            company=company,
            actor=actor,
            message=f"Plan changed to {plan.code}",
        )
        return sub

    @classmethod
    def cancel(cls, company: Company, *, at_period_end: bool = True, actor=None) -> Subscription:
        sub = company.subscription
        if at_period_end:
            sub.cancel_at_period_end = True
            sub.save(update_fields=["cancel_at_period_end", "updated_at"])
        else:
            sub.status = Subscription.Status.CANCELLED
            sub.cancel_at_period_end = False
            sub.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
        AuditService.log(
            action="billing.cancelled",
            company=company,
            actor=actor,
            message="Subscription cancelled",
        )
        return sub

    @classmethod
    def check_limits(cls, company: Company) -> dict:
        try:
            sub = company.subscription
        except Subscription.DoesNotExist:
            return {"allowed": True, "warnings": ["No subscription — unrestricted trial mode"]}
        plan = sub.plan
        usage = snapshot_usage(company)
        warnings = []
        allowed = sub.is_usable
        if usage.get(UsageRecord.Metric.TICKETS, 0) >= plan.max_tickets_per_month:
            warnings.append("Monthly ticket limit reached")
            allowed = False
        if usage.get(UsageRecord.Metric.AGENTS, 0) > plan.max_agents:
            warnings.append("Agent seat limit exceeded")
        if usage.get(UsageRecord.Metric.ASSETS, 0) > plan.max_assets:
            warnings.append("Asset limit exceeded")
        return {
            "allowed": allowed,
            "warnings": warnings,
            "usage": usage,
            "plan": plan.code,
            "status": sub.status,
        }

    @classmethod
    @transaction.atomic
    def generate_invoice(cls, company: Company, actor=None) -> Invoice:
        sub = getattr(company, "subscription", None)
        plan = sub.plan if sub else None
        start, end = current_period()
        amount = plan.price_monthly if plan else Decimal("0")
        seats = sub.seats if sub else 1
        subtotal = amount * Decimal(seats)
        number = f"INV-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"
        invoice = Invoice.objects.create(
            company=company,
            subscription=sub,
            number=number,
            status=Invoice.Status.OPEN,
            currency=plan.currency if plan else "USD",
            subtotal=subtotal,
            tax=Decimal("0"),
            total=subtotal,
            period_start=start,
            period_end=end,
            due_date=end + timedelta(days=14),
            line_items=[
                {
                    "description": f"{plan.name if plan else 'Usage'} x {seats} seats",
                    "quantity": seats,
                    "unit_amount": str(amount),
                    "amount": str(subtotal),
                }
            ],
            created_by=actor,
        )
        return invoice

    @classmethod
    def mark_paid(cls, invoice: Invoice, actor=None) -> Invoice:
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["status", "paid_at", "updated_at"])
        if invoice.subscription_id:
            sub = invoice.subscription
            sub.status = Subscription.Status.ACTIVE
            sub.save(update_fields=["status", "updated_at"])
        AuditService.log(
            action="billing.invoice_paid",
            company=invoice.company,
            actor=actor,
            message=invoice.number,
            object_type="invoice",
            object_id=str(invoice.pk),
        )
        return invoice