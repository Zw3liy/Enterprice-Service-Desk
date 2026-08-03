"""Tenant provisioning and isolation helpers."""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils.text import slugify

from apps.multi_tenant.models import TenantDomain, TenantSettings
from apps.service_desk.models import Company, Department, Priority, Queue, Status

logger = logging.getLogger(__name__)


class TenantService:
    @staticmethod
    @transaction.atomic
    def provision(
        name: str,
        slug: str | None = None,
        admin_email: str = "",
        domain: str = "",
    ) -> Company:
        slug = slug or slugify(name)[:220]
        company, created = Company.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "primary_email": admin_email, "is_active": True},
        )
        TenantSettings.objects.get_or_create(
            company=company,
            defaults={
                "feature_flags": {
                    "ai": True,
                    "cmdb": True,
                    "change": True,
                    "portal": True,
                },
                "branding": {"product_name": name},
            },
        )
        if domain:
            TenantDomain.objects.update_or_create(
                domain=domain.lower().strip(),
                defaults={
                    "company": company,
                    "is_primary": True,
                    "is_verified": False,
                    "is_active": True,
                },
            )
        if not created:
            return company

        Department.objects.get_or_create(
            company=company, code="it", defaults={"name": "IT"}
        )
        for code, label, rank, colour, category, terminal in [
            ("new", "New", 10, "#0d6efd", Status.CategoryChoice.NEW, False),
            ("open", "Open", 20, "#2563eb", Status.CategoryChoice.IN_PROGRESS, False),
            ("resolved", "Resolved", 50, "#059669", Status.CategoryChoice.RESOLVED, False),
            ("closed", "Closed", 60, "#6b7280", Status.CategoryChoice.CLOSED, True),
        ]:
            Status.objects.get_or_create(
                company=company,
                code=code,
                defaults={
                    "name": label,
                    "rank": rank,
                    "colour": colour,
                    "is_terminal": terminal,
                    "category": category,
                },
            )
        for code, label, rank in [
            ("critical", "Critical", 10),
            ("high", "High", 20),
            ("medium", "Medium", 30),
            ("low", "Low", 40),
        ]:
            Priority.objects.get_or_create(
                company=company, code=code, defaults={"name": label, "rank": rank}
            )
        Queue.objects.get_or_create(
            company=company, code="service-desk", defaults={"name": "Service Desk"}
        )
        logger.info("tenant_provisioned slug=%s", company.slug)
        return company

    @staticmethod
    def resolve_by_domain(host: str) -> Optional[Company]:
        host = (host or "").split(":")[0].lower().strip()
        if not host:
            return None
        mapping = (
            TenantDomain.objects.filter(domain=host, is_active=True)
            .select_related("company")
            .first()
        )
        if mapping and mapping.company.is_active:
            return mapping.company
        return None

    @staticmethod
    def feature_enabled(company: Company, flag: str) -> bool:
        settings_obj = TenantSettings.objects.filter(company_id=company.pk).first()
        if settings_obj is None:
            return True
        flags = settings_obj.feature_flags or {}
        if flag not in flags:
            return True
        return bool(flags.get(flag))

    @staticmethod
    def set_feature(company: Company, flag: str, enabled: bool) -> TenantSettings:
        settings_obj, _ = TenantSettings.objects.get_or_create(company=company)
        flags = dict(settings_obj.feature_flags or {})
        flags[flag] = enabled
        settings_obj.feature_flags = flags
        settings_obj.save(update_fields=["feature_flags", "updated_at"])
        return settings_obj
