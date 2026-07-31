"""Tenant data isolation helpers for querysets."""

from __future__ import annotations


def filter_by_company(queryset, company, field: str = "company"):
    if company is None:
        return queryset.none()
    return queryset.filter(**{field: company})


def assert_same_tenant(obj_company_id, company_id) -> bool:
    return obj_company_id == company_id
