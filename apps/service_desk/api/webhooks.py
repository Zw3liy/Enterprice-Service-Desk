"""Outbound webhook delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import urllib.request

from apps.service_desk.models import WebhookEndpoint

logger = logging.getLogger(__name__)


def dispatch_webhooks(company, event: str, payload: dict[str, Any]) -> int:
    if company is None:
        return 0
    endpoints = WebhookEndpoint.objects.filter(company=company, is_active=True)
    sent = 0
    body = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    for ep in endpoints:
        events = ep.events or []
        if events and event not in events:
            continue
        headers = {"Content-Type": "application/json", **(ep.headers or {})}
        if ep.secret:
            sig = hmac.new(ep.secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-ESD-Signature"] = sig
        req = urllib.request.Request(ep.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                logger.info("webhook url=%s status=%s", ep.url, resp.status)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("webhook failed url=%s err=%s", ep.url, exc)
    return sent
