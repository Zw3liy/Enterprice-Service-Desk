"""Centralised audit logging."""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model

from apps.service_desk.middleware import get_client_ip, get_current_request
from apps.service_desk.models import AuditLog, Company, Ticket

logger = logging.getLogger(__name__)
User = get_user_model()


class AuditService:
    @staticmethod
    def log(
        *,
        action: str,
        message: str = "",
        ticket: Optional[Ticket] = None,
        company: Optional[Company] = None,
        actor=None,
        object_type: str = "",
        object_id: str = "",
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        request = get_current_request()
        if actor is None and request is not None and getattr(request, "user", None):
            if request.user.is_authenticated:
                actor = request.user
        if ip_address is None:
            ip_address = get_client_ip(request)
        if company is None and ticket is not None:
            company = ticket.company
        if not object_type and ticket is not None:
            object_type = "ticket"
            object_id = str(ticket.pk)

        entry = AuditLog.objects.create(
            action=action,
            message=message,
            ticket=ticket,
            company=company,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            object_type=object_type,
            object_id=object_id,
            metadata=metadata or {},
            ip_address=ip_address,
        )
        logger.info("audit action=%s object=%s:%s", action, object_type, object_id)
        return entry
