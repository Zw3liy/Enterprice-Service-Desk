"""Integration connector registry and health checks."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.integrations.models import IntegrationConnection

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    @staticmethod
    def upsert(
        company,
        *,
        provider: str,
        name: str,
        config: dict | None = None,
        user=None,
    ) -> IntegrationConnection:
        conn, _ = IntegrationConnection.objects.update_or_create(
            company=company,
            provider=provider,
            name=name,
            defaults={
                "config": config or {},
                "state": IntegrationConnection.State.CONFIGURED,
                "created_by": user,
                "last_error": "",
            },
        )
        return conn

    @staticmethod
    def mark_active(conn: IntegrationConnection) -> IntegrationConnection:
        conn.state = IntegrationConnection.State.ACTIVE
        conn.last_synced_at = timezone.now()
        conn.last_error = ""
        conn.save(update_fields=["state", "last_synced_at", "last_error", "updated_at"])
        return conn

    @staticmethod
    def mark_error(conn: IntegrationConnection, error: str) -> IntegrationConnection:
        conn.state = IntegrationConnection.State.ERROR
        conn.last_error = error[:2000]
        conn.save(update_fields=["state", "last_error", "updated_at"])
        return conn

    @classmethod
    def test_connection(cls, conn: IntegrationConnection) -> dict[str, Any]:
        provider = conn.provider
        cfg = conn.config or {}
        try:
            if provider == IntegrationConnection.Provider.EMAIL_IMAP:
                if not cfg.get("host"):
                    raise ValueError("IMAP host required")
                result = {"ok": True, "provider": provider, "host": cfg.get("host")}
            elif provider == IntegrationConnection.Provider.LDAP:
                if not cfg.get("server"):
                    raise ValueError("LDAP server required")
                result = {"ok": True, "provider": provider, "server": cfg.get("server")}
            elif provider == IntegrationConnection.Provider.M365:
                if not cfg.get("tenant_id") or not cfg.get("client_id"):
                    raise ValueError("tenant_id and client_id required")
                result = {"ok": True, "provider": provider}
            elif provider in {
                IntegrationConnection.Provider.SLACK,
                IntegrationConnection.Provider.TEAMS,
            }:
                if not cfg.get("webhook_url"):
                    raise ValueError("webhook_url required")
                result = {"ok": True, "provider": provider}
            else:
                result = {"ok": True, "provider": provider}
            cls.mark_active(conn)
            return result
        except Exception as exc:  # noqa: BLE001
            cls.mark_error(conn, str(exc))
            logger.warning("connector_test_failed id=%s err=%s", conn.pk, exc)
            return {"ok": False, "error": str(exc), "provider": provider}
