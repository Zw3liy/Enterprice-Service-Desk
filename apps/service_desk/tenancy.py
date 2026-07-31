"""Tenant (company) resolution helpers."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest

from apps.service_desk.models import AgentProfile, Company, Contact


def get_active_company(request: HttpRequest) -> Company | None:
    """Resolve the active company for the current request/user."""
    company_id = request.session.get("company_id")
    if company_id:
        company = Company.objects.filter(pk=company_id, is_active=True).first()
        if company:
            return company

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile = AgentProfile.objects.filter(user=user).select_related("company").first()
        if profile and profile.company_id:
            request.session["company_id"] = profile.company_id
            return profile.company
        contact = Contact.objects.filter(user=user).select_related("company").first()
        if contact:
            request.session["company_id"] = contact.company_id
            return contact.company

    slug = getattr(settings, "ESD_DEFAULT_COMPANY_SLUG", "default")
    company = Company.objects.filter(slug=slug, is_active=True).first()
    if company is None:
        company = Company.objects.filter(is_active=True).order_by("id").first()
    if company is not None:
        request.session["company_id"] = company.pk
    return company


def require_company(request: HttpRequest) -> Company:
    company = get_active_company(request)
    if company is None:
        raise ImproperlyConfigured(
            "No active company configured. Run: python manage.py bootstrap_esd"
        )
    return company


def set_active_company(request: HttpRequest, company: Company) -> None:
    request.session["company_id"] = company.pk
