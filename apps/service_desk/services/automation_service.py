"""Rule engine for ticket automations."""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model

from apps.service_desk.models import AutomationRule, Status, Ticket
from apps.service_desk.services.assignment_service import AssignmentService
from apps.service_desk.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
User = get_user_model()


class AutomationService:
    @classmethod
    def dispatch(
        cls,
        trigger: str,
        *,
        ticket: Ticket,
        comment=None,
        extra: Optional[dict] = None,
    ) -> list[str]:
        if not ticket.company_id:
            return []
        rules = (
            AutomationRule.objects.filter(
                company=ticket.company, trigger=trigger, is_active=True
            )
            .order_by("priority", "id")
        )
        applied: list[str] = []
        context = {
            "ticket": ticket,
            "comment": comment,
            "extra": extra or {},
            "status_code": ticket.status.code if ticket.status_id else "",
            "priority_code": ticket.priority.code if ticket.priority_id else "",
            "queue_code": ticket.queue.code if ticket.queue_id else "",
            "ticket_type": ticket.ticket_type,
            "tags": ticket.tags or [],
        }
        for rule in rules:
            if not cls._match(rule.conditions or {}, context):
                continue
            cls._execute(rule.actions or [], ticket, context)
            applied.append(rule.name)
            logger.info(
                "automation rule=%s trigger=%s ticket=%s",
                rule.name,
                trigger,
                ticket.ticket_number,
            )
            if rule.stop_processing:
                break
        return applied

    @staticmethod
    def _match(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
        if not conditions:
            return True
        for key, expected in conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected and not (
                    isinstance(actual, list) and set(expected) & set(actual)
                ):
                    return False
            elif actual != expected:
                return False
        return True

    @classmethod
    def _execute(cls, actions: list, ticket: Ticket, context: dict) -> None:
        for action in actions:
            if not isinstance(action, dict):
                continue
            kind = action.get("type") or action.get("action")
            if kind == "set_status":
                code = action.get("status_code") or action.get("code")
                if code and ticket.company_id:
                    status = Status.objects.filter(
                        company=ticket.company, code=code, is_active=True
                    ).first()
                    if status:
                        ticket.status = status
                        if status.category == Status.CategoryChoice.RESOLVED:
                            ticket.mark_resolved()
                        if status.category == Status.CategoryChoice.CLOSED:
                            ticket.mark_closed()
                        ticket.save()
            elif kind == "add_tag":
                tag = action.get("tag")
                if tag:
                    tags = list(ticket.tags or [])
                    if tag not in tags:
                        tags.append(tag)
                        ticket.tags = tags
                        ticket.save(update_fields=["tags", "updated_at"])
            elif kind == "assign_user":
                username = action.get("username")
                user_id = action.get("user_id")
                user = None
                if user_id:
                    user = User.objects.filter(pk=user_id).first()
                elif username:
                    user = User.objects.filter(username=username).first()
                if user:
                    AssignmentService.assign(ticket, assignee=user, note="Automation")
            elif kind == "auto_assign":
                AssignmentService.auto_assign(ticket)
            elif kind == "notify":
                message = action.get("message") or "Automation notification"
                subject = action.get("subject") or f"[{ticket.ticket_number}] Notice"
                recipients = []
                if ticket.assignee_id:
                    recipients.append(ticket.assignee)
                NotificationService.notify_many(
                    recipients,
                    subject=subject,
                    body=message,
                    ticket=ticket,
                    send_email=bool(action.get("email")),
                )
            elif kind == "set_priority_rank_min":
                # no-op friendly placeholder for future ranking logic
                pass
            else:
                logger.debug("unknown automation action type=%s", kind)
