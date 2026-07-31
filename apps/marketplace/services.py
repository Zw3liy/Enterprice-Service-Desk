from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.marketplace.models import InstalledApp, MarketplaceApp
from apps.service_desk.models import WebhookEndpoint
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)

DEFAULT_APPS = [
    {
        "slug": "slack-notify",
        "name": "Slack Notifications",
        "vendor": "Slack",
        "category": MarketplaceApp.Category.COMMUNICATION,
        "short_description": "Post ticket events to Slack channels",
        "config_schema": {"webhook_url": "string", "channel": "string"},
        "webhook_events": ["ticket.created", "ticket.updated", "sla.breached"],
        "icon": "fa-slack",
    },
    {
        "slug": "teams-notify",
        "name": "Microsoft Teams",
        "vendor": "Microsoft",
        "category": MarketplaceApp.Category.COMMUNICATION,
        "short_description": "Notify Teams channels on ticket lifecycle events",
        "config_schema": {"webhook_url": "string"},
        "webhook_events": ["ticket.created", "ticket.assigned"],
        "icon": "fa-microsoft",
    },
    {
        "slug": "pagerduty",
        "name": "PagerDuty",
        "vendor": "PagerDuty",
        "category": MarketplaceApp.Category.MONITORING,
        "short_description": "Escalate major incidents to on-call",
        "config_schema": {"routing_key": "string"},
        "webhook_events": ["incident.major_declared", "sla.breached"],
        "icon": "fa-bell",
        "is_premium": True,
    },
    {
        "slug": "github-issues",
        "name": "GitHub Issues",
        "vendor": "GitHub",
        "category": MarketplaceApp.Category.DEVOPS,
        "short_description": "Create GitHub issues from change tasks",
        "config_schema": {"token": "string", "repo": "string"},
        "webhook_events": ["change.completed"],
        "icon": "fa-github",
    },
    {
        "slug": "azure-ad-sync",
        "name": "Azure AD Sync",
        "vendor": "Microsoft",
        "category": MarketplaceApp.Category.IDENTITY,
        "short_description": "Sync users and groups from Azure AD",
        "config_schema": {
            "tenant_id": "string",
            "client_id": "string",
            "client_secret": "string",
        },
        "webhook_events": [],
        "icon": "fa-cloud",
        "is_premium": True,
    },
]


class MarketplaceService:
    @staticmethod
    def seed_catalog() -> int:
        created = 0
        for data in DEFAULT_APPS:
            _, was_created = MarketplaceApp.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "vendor": data.get("vendor") or "",
                    "category": data.get("category") or MarketplaceApp.Category.OTHER,
                    "short_description": data.get("short_description") or "",
                    "description": data.get("description") or data.get("short_description") or "",
                    "icon": data.get("icon") or "fa-puzzle-piece",
                    "config_schema": data.get("config_schema") or {},
                    "webhook_events": data.get("webhook_events") or [],
                    "is_published": True,
                    "is_premium": data.get("is_premium") or False,
                },
            )
            if was_created:
                created += 1
        return created

    @classmethod
    @transaction.atomic
    def install(
        cls,
        company,
        app_slug: str,
        *,
        config: dict | None = None,
        user=None,
    ) -> InstalledApp:
        cls.seed_catalog()
        app = MarketplaceApp.objects.get(slug=app_slug, is_published=True)
        config = config or {}
        # basic required key validation
        for key in (app.config_schema or {}).keys():
            if key not in config or config.get(key) in (None, ""):
                raise ValueError(f"Missing required config key: {key}")
        install, _ = InstalledApp.objects.update_or_create(
            company=company,
            app=app,
            defaults={
                "state": InstalledApp.State.INSTALLED,
                "config": config,
                "installed_by": user,
                "error_message": "",
                "last_sync_at": timezone.now(),
            },
        )
        # auto-create webhook endpoint when app provides webhook_url
        webhook_url = config.get("webhook_url")
        if webhook_url:
            WebhookEndpoint.objects.update_or_create(
                company=company,
                name=f"{app.name} integration",
                defaults={
                    "url": webhook_url,
                    "events": app.webhook_events or [],
                    "is_active": True,
                    "headers": {"X-ESD-App": app.slug},
                },
            )
        AuditService.log(
            action="marketplace.installed",
            company=company,
            actor=user,
            message=f"Installed {app.slug}",
            object_type="installed_app",
            object_id=str(install.pk),
        )
        logger.info("marketplace_install company=%s app=%s", company.slug, app.slug)
        return install

    @classmethod
    def disable(cls, install: InstalledApp, user=None) -> InstalledApp:
        install.state = InstalledApp.State.DISABLED
        install.save(update_fields=["state", "updated_at"])
        AuditService.log(
            action="marketplace.disabled",
            company=install.company,
            actor=user,
            message=install.app.slug,
            object_type="installed_app",
            object_id=str(install.pk),
        )
        return install

    @staticmethod
    def catalog(query: str = ""):
        qs = MarketplaceApp.objects.filter(is_published=True)
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(short_description__icontains=query)
        return qs.distinct()
