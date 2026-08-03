"""SIEM export helpers for audit events (CEF / JSON lines)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable

from apps.service_desk.models import AuditLog


def audit_to_cef(entry: AuditLog) -> str:
    """Common Event Format line."""
    ts = entry.created_at.strftime("%b %d %Y %H:%M:%S") if entry.created_at else ""
    device_vendor = "EnterpriseServiceDesk"
    device_product = "ESD"
    device_version = "1.0"
    signature_id = entry.action or "audit"
    name = (entry.message or entry.action or "event")[:128]
    severity = 5
    extensions = [
        f"src={entry.ip_address or '0.0.0.0'}",
        f"suser={getattr(entry.actor, 'username', '') if entry.actor_id else ''}",
        f"cs1={entry.object_type}",
        f"cs1Label=objectType",
        f"cs2={entry.object_id}",
        f"cs2Label=objectId",
        f"msg={_escape(entry.message or '')}",
    ]
    return (
        f"CEF:0|{device_vendor}|{device_product}|{device_version}|{signature_id}|"
        f"{_escape(name)}|{severity}|{' '.join(extensions)}"
    )


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace("\n", " ")
        .replace("|", "\\|")
    )


def audit_to_json(entry: AuditLog) -> str:
    return json.dumps(
        {
            "timestamp": entry.created_at.isoformat() if entry.created_at else None,
            "action": entry.action,
            "message": entry.message,
            "actor": getattr(entry.actor, "username", None) if entry.actor_id else None,
            "company_id": entry.company_id,
            "ticket_id": entry.ticket_id,
            "object_type": entry.object_type,
            "object_id": entry.object_id,
            "ip_address": entry.ip_address,
            "metadata": entry.metadata,
        },
        default=str,
    )


def export_queryset(qs: Iterable[AuditLog], fmt: str = "json") -> str:
    lines = []
    for entry in qs:
        if fmt == "cef":
            lines.append(audit_to_cef(entry))
        else:
            lines.append(audit_to_json(entry))
    return "\n".join(lines) + ("\n" if lines else "")


def recent_export(company=None, limit: int = 500, fmt: str = "json") -> str:
    qs = AuditLog.objects.select_related("actor", "company", "ticket").order_by("-created_at")
    if company is not None:
        qs = qs.filter(company=company)
    return export_queryset(qs[:limit], fmt=fmt)
