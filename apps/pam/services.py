from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.pam.models import AccessRequest, PrivilegedAccount, PrivilegedSession
from apps.service_desk.services.audit_service import AuditService
from apps.service_desk.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class PAMService:
    @staticmethod
    def register_account(company, *, name: str, system: str, username: str, **kwargs) -> PrivilegedAccount:
        return PrivilegedAccount.objects.create(
            company=company,
            name=name,
            system=system,
            username=username,
            **kwargs,
        )

    @classmethod
    @transaction.atomic
    def request_access(
        cls,
        account: PrivilegedAccount,
        requester,
        *,
        justification: str,
        minutes: int = 60,
        approver=None,
    ) -> AccessRequest:
        req = AccessRequest.objects.create(
            company=account.company,
            account=account,
            requester=requester,
            approver=approver,
            justification=justification,
            requested_minutes=max(5, min(minutes, 24 * 60)),
        )
        if approver:
            NotificationService.create(
                recipient=approver,
                subject=f"PAM approval: {account}",
                body=justification,
                send_email=True,
            )
        AuditService.log(
            action="pam.requested",
            company=account.company,
            actor=requester,
            message=str(account),
            object_type="pam_request",
            object_id=str(req.pk),
        )
        return req

    @classmethod
    @transaction.atomic
    def decide(
        cls,
        request_obj: AccessRequest,
        *,
        approved: bool,
        actor=None,
        note: str = "",
    ) -> AccessRequest:
        request_obj.state = (
            AccessRequest.State.APPROVED if approved else AccessRequest.State.DENIED
        )
        request_obj.approver = actor
        request_obj.decision_note = note
        request_obj.decided_at = timezone.now()
        if approved:
            request_obj.starts_at = timezone.now()
            request_obj.ends_at = timezone.now() + timedelta(
                minutes=request_obj.requested_minutes
            )
        request_obj.save()
        NotificationService.create(
            recipient=request_obj.requester,
            subject=f"PAM request {request_obj.state}",
            body=note or request_obj.justification,
            send_email=True,
        )
        AuditService.log(
            action="pam.decided",
            company=request_obj.company,
            actor=actor,
            message=request_obj.state,
            object_type="pam_request",
            object_id=str(request_obj.pk),
            metadata={"approved": approved},
        )
        return request_obj

    @classmethod
    @transaction.atomic
    def start_session(
        cls, request_obj: AccessRequest, *, client_ip: str | None = None
    ) -> PrivilegedSession:
        if request_obj.state != AccessRequest.State.APPROVED:
            raise ValueError("Access request is not approved")
        if request_obj.ends_at and timezone.now() > request_obj.ends_at:
            request_obj.state = AccessRequest.State.EXPIRED
            request_obj.save(update_fields=["state", "updated_at"])
            raise ValueError("Access window expired")
        session = PrivilegedSession.objects.create(
            access_request=request_obj,
            session_token=secrets.token_urlsafe(32),
            client_ip=client_ip,
            audit_trail=[{"event": "started", "at": timezone.now().isoformat()}],
        )
        AuditService.log(
            action="pam.session_started",
            company=request_obj.company,
            actor=request_obj.requester,
            message=str(request_obj.account),
            object_type="pam_session",
            object_id=str(session.pk),
        )
        return session

    @classmethod
    def end_session(cls, session: PrivilegedSession, note: str = "") -> PrivilegedSession:
        session.state = PrivilegedSession.State.ENDED
        session.ended_at = timezone.now()
        trail = list(session.audit_trail or [])
        trail.append({"event": "ended", "note": note, "at": timezone.now().isoformat()})
        session.audit_trail = trail
        session.save()
        return session

    @staticmethod
    def expire_due() -> int:
        now = timezone.now()
        return AccessRequest.objects.filter(
            state=AccessRequest.State.APPROVED, ends_at__lt=now
        ).update(state=AccessRequest.State.EXPIRED)
