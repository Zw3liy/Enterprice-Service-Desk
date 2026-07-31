from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from apps.it_financial_management.models import Budget, ChargebackEntry, CostCenter
from apps.service_desk.models import WorkLog


class ITFinancialService:
    @staticmethod
    def ensure_cost_center(company, code: str, name: str = "", department=None) -> CostCenter:
        code = slugify(code)[:40]
        cc, _ = CostCenter.objects.get_or_create(
            company=company,
            code=code,
            defaults={"name": name or code.upper(), "department": department},
        )
        return cc

    @staticmethod
    def set_budget(cost_center: CostCenter, fiscal_year: int, amount, currency: str = "ZAR") -> Budget:
        budget, _ = Budget.objects.update_or_create(
            cost_center=cost_center,
            fiscal_year=fiscal_year,
            defaults={
                "company": cost_center.company,
                "amount": amount,
                "currency": currency,
            },
        )
        return budget

    @staticmethod
    def post_chargeback(
        cost_center: CostCenter,
        *,
        description: str,
        amount,
        category: str = ChargebackEntry.Category.LABOR,
        ticket=None,
        posted_on: date | None = None,
        currency: str = "ZAR",
        user=None,
    ) -> ChargebackEntry:
        return ChargebackEntry.objects.create(
            company=cost_center.company,
            cost_center=cost_center,
            category=category,
            description=description,
            amount=amount,
            currency=currency,
            ticket=ticket,
            posted_on=posted_on or timezone.localdate(),
            created_by=user,
        )

    @staticmethod
    def charge_worklog(worklog: WorkLog, cost_center: CostCenter, hourly_rate=Decimal("750.00"), user=None):
        amount = (Decimal(worklog.minutes_spent) / Decimal("60")) * Decimal(str(hourly_rate))
        return ITFinancialService.post_chargeback(
            cost_center,
            description=f"Labor {worklog.minutes_spent}m on {worklog.ticket.ticket_number}",
            amount=amount.quantize(Decimal("0.01")),
            category=ChargebackEntry.Category.LABOR,
            ticket=worklog.ticket,
            user=user,
        )

    @staticmethod
    def budget_vs_actual(cost_center: CostCenter, fiscal_year: int) -> dict:
        budget = Budget.objects.filter(
            cost_center=cost_center, fiscal_year=fiscal_year
        ).first()
        spent = (
            ChargebackEntry.objects.filter(
                cost_center=cost_center, posted_on__year=fiscal_year
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        amount = budget.amount if budget else Decimal("0")
        remaining = amount - spent
        return {
            "budget": amount,
            "spent": spent,
            "remaining": remaining,
            "utilization_pct": round(float((spent / amount) * 100), 1) if amount else None,
            "currency": budget.currency if budget else "ZAR",
            "fiscal_year": fiscal_year,
            "cost_center": cost_center.code,
        }
