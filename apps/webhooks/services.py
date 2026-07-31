"""Outbound webhook dispatch with delivery logging."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.utils import timezone

from apps.service_desk.models import Company, WebhookEndpoint
from apps.webhooks.models import WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookService:
    @classmethod
    def dispatch(
        cls,
        company: Company | None,
        event: str,
        payload: dict[str, Any],
        *,
        timeout: int = 10,
    ) -> list[WebhookDelivery]:
        if company is None:
            return []
        endpoints = WebhookEndpoint.objects.filter(company=company, is_active=True)
        deliveries: list[WebhookDelivery] = []
        body_obj = {"event": event, "payload": payload, "timestamp": timezone.now().isoformat()}
        body = json.dumps(body_obj, default=str).encode("utf-8")
        for ep in endpoints:
            events = ep.events or []
            if events and event not in events and "*" not in events:
                continue
            delivery = WebhookDelivery.objects.create(
                company=company,
                endpoint=ep,
                event=event,
                payload=body_obj,
                status=WebhookDelivery.Status.PENDING,
            )
            headers = {"Content-Type": "application/json", **(ep.headers or {})}
            if ep.secret:
                sig = hmac.new(ep.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
                headers["X-ESD-Signature"] = f"sha256={sig}"
            req = urllib.request.Request(ep.url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    response_body = resp.read().decode("utf-8", errors="replace")[:4000]
                    delivery.status = WebhookDelivery.Status.SUCCESS
                    delivery.response_code = getattr(resp, "status", 200)
                    delivery.response_body = response_body
                    delivery.delivered_at = timezone.now()
            except urllib.error.HTTPError as exc:
                delivery.status = WebhookDelivery.Status.FAILED
                delivery.response_code = exc.code
                delivery.error_message = str(exc)
                try:
                    delivery.response_body = exc.read().decode("utf-8", errors="replace")[:4000]
                except Exception:  # noqa: BLE001
                    pass
            except Exception as exc:  # noqa: BLE001
                delivery.status = WebhookDelivery.Status.FAILED
                delivery.error_message = str(exc)
                logger.warning("webhook_failed endpoint=%s err=%s", ep.pk, exc)
            delivery.save()
            deliveries.append(delivery)
        return deliveries

    @staticmethod
    def recent(company: Company, limit: int = 50):
        return WebhookDelivery.objects.filter(company=company).select_related("endpoint")[:limit]