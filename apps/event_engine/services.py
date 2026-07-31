from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from django.dispatch import Signal

from apps.event_engine.models import DomainEvent

logger = logging.getLogger(__name__)

# In-process signal bus
domain_event_signal = Signal()  # providing_args historically: event_type, payload, company


class EventBus:
    _handlers: dict[str, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable) -> None:
        cls._handlers.setdefault(event_type, []).append(handler)
        cls._handlers.setdefault("*", [])

    @classmethod
    def publish(
        cls,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        company=None,
        aggregate_type: str = "",
        aggregate_id: str = "",
        metadata: dict | None = None,
        correlation_id: str = "",
        persist: bool = True,
    ) -> DomainEvent | None:
        payload = payload or {}
        correlation_id = correlation_id or uuid.uuid4().hex
        event = None
        if persist:
            event = DomainEvent.objects.create(
                company=company,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id or ""),
                payload=payload,
                metadata=metadata or {},
                correlation_id=correlation_id,
            )
        domain_event_signal.send(
            sender=EventBus,
            event_type=event_type,
            payload=payload,
            company=company,
            event=event,
        )
        for handler in cls._handlers.get(event_type, []) + cls._handlers.get("*", []):
            try:
                handler(event_type=event_type, payload=payload, company=company, event=event)
            except Exception:  # noqa: BLE001
                logger.exception("event_handler_failed type=%s", event_type)
        logger.info("event_published type=%s aggregate=%s:%s", event_type, aggregate_type, aggregate_id)
        return event

    @staticmethod
    def recent(company=None, event_type: str = "", limit: int = 100):
        qs = DomainEvent.objects.all()
        if company is not None:
            qs = qs.filter(company=company)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs[:limit]
