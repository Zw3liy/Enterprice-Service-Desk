from __future__ import annotations

import logging
import secrets
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.offline_sync.models import OfflineMutation, SyncCursor
from apps.service_desk.models import Ticket, TicketComment
from apps.service_desk.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class OfflineSyncService:
    @staticmethod
    def get_or_create_cursor(company, user, device_id: str) -> SyncCursor:
        cursor, _ = SyncCursor.objects.get_or_create(
            company=company,
            user=user,
            device_id=device_id,
            defaults={"cursor_token": secrets.token_urlsafe(16)},
        )
        if not cursor.cursor_token:
            cursor.cursor_token = secrets.token_urlsafe(16)
            cursor.save(update_fields=["cursor_token", "updated_at"])
        return cursor

    @classmethod
    def pull(cls, company, user, device_id: str, since=None) -> dict[str, Any]:
        cursor = cls.get_or_create_cursor(company, user, device_id)
        since = since or cursor.last_pulled_at
        tickets_qs = TicketService.search(company=company, mine_user=user)
        if since:
            tickets_qs = tickets_qs.filter(updated_at__gte=since)
        tickets = [
            {
                "id": t.pk,
                "ticket_number": t.ticket_number,
                "title": t.title,
                "description": t.description,
                "status_id": t.status_id,
                "priority_id": t.priority_id,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tickets_qs[:200]
        ]
        cursor.last_pulled_at = timezone.now()
        cursor.save(update_fields=["last_pulled_at", "updated_at"])
        return {
            "cursor_token": cursor.cursor_token,
            "pulled_at": cursor.last_pulled_at.isoformat(),
            "tickets": tickets,
        }

    @classmethod
    @transaction.atomic
    def push(
        cls,
        company,
        user,
        device_id: str,
        mutations: list[dict],
    ) -> list[OfflineMutation]:
        cursor = cls.get_or_create_cursor(company, user, device_id)
        results: list[OfflineMutation] = []
        for item in mutations:
            mut, created = OfflineMutation.objects.get_or_create(
                company=company,
                user=user,
                device_id=device_id,
                client_mutation_id=str(item.get("client_mutation_id") or secrets.token_hex(8)),
                defaults={
                    "entity_type": item.get("entity_type") or "ticket",
                    "entity_id": str(item.get("entity_id") or ""),
                    "operation": item.get("operation") or "update",
                    "payload": item.get("payload") or {},
                },
            )
            if not created and mut.state == OfflineMutation.State.APPLIED:
                results.append(mut)
                continue
            try:
                result = cls._apply(mut, user=user)
                mut.state = OfflineMutation.State.APPLIED
                mut.result = result
                mut.applied_at = timezone.now()
                mut.error_message = ""
            except Exception as exc:  # noqa: BLE001
                logger.exception("offline_mutation_failed")
                mut.state = OfflineMutation.State.FAILED
                mut.error_message = str(exc)
            mut.save()
            results.append(mut)
        cursor.last_pushed_at = timezone.now()
        cursor.save(update_fields=["last_pushed_at", "updated_at"])
        return results

    @staticmethod
    def _apply(mut: OfflineMutation, user=None) -> dict:
        payload = mut.payload or {}
        if mut.entity_type == "ticket" and mut.operation == "comment":
            ticket = Ticket.objects.get(pk=int(mut.entity_id or payload.get("ticket_id")))
            comment = TicketService.add_comment(
                ticket,
                body=payload.get("body") or "",
                author=user,
                is_internal=bool(payload.get("is_internal")),
            )
            return {"comment_id": comment.pk}
        if mut.entity_type == "ticket" and mut.operation == "create":
            ticket = TicketService.create_ticket(
                title=payload.get("title") or "Offline ticket",
                description=payload.get("description") or "",
                company=mut.company,
                requester_user=user,
                actor=user,
                channel=Ticket.Channel.API,
                run_ai=False,
            )
            return {"ticket_id": ticket.pk, "ticket_number": ticket.ticket_number}
        if mut.entity_type == "ticket" and mut.operation == "update":
            ticket = Ticket.objects.get(pk=int(mut.entity_id or payload.get("ticket_id")))
            fields = {}
            if "title" in payload:
                fields["title"] = payload["title"]
            if "description" in payload:
                fields["description"] = payload["description"]
            if fields:
                TicketService.update_ticket(ticket, actor=user, **fields)
            return {"ticket_id": ticket.pk}
        raise ValueError(f"Unsupported mutation {mut.entity_type}.{mut.operation}")
