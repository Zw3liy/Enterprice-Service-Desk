from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import Change, ChangeApproval, ChangeHistory

User = get_user_model()


class ChangeService:
    """
    Change Management business service.

    Risk level is *calculated* (impact x urgency, via RISK_MATRIX) at
    assessment time, then stored — "calculated or governed risk
    level" per the mission spec: calculated by default, and a CAB
    decision (approve/reject) is the governance step that acts on it.
    """

    STATUS_FLOW = {
        Change.STATUS_DRAFT: [Change.STATUS_SUBMITTED],
        Change.STATUS_SUBMITTED: [
            Change.STATUS_ASSESSED,
            Change.STATUS_REJECTED,
        ],
        Change.STATUS_ASSESSED: [
            Change.STATUS_APPROVED,
            Change.STATUS_REJECTED,
        ],
        Change.STATUS_APPROVED: [Change.STATUS_SCHEDULED],
        Change.STATUS_SCHEDULED: [Change.STATUS_IMPLEMENTING],
        Change.STATUS_IMPLEMENTING: [
            Change.STATUS_VALIDATION,
            Change.STATUS_FAILED,
        ],
        Change.STATUS_VALIDATION: [
            Change.STATUS_COMPLETED,
            Change.STATUS_FAILED,
        ],
        Change.STATUS_FAILED: [Change.STATUS_ROLLED_BACK],
        Change.STATUS_COMPLETED: [],
        Change.STATUS_REJECTED: [],
        Change.STATUS_ROLLED_BACK: [],
    }

    RISK_MATRIX = {
        ("low", "low"): Change.RISK_LOW,
        ("low", "medium"): Change.RISK_LOW,
        ("low", "high"): Change.RISK_MEDIUM,
        ("medium", "low"): Change.RISK_LOW,
        ("medium", "medium"): Change.RISK_MEDIUM,
        ("medium", "high"): Change.RISK_HIGH,
        ("high", "low"): Change.RISK_MEDIUM,
        ("high", "medium"): Change.RISK_HIGH,
        ("high", "high"): Change.RISK_CRITICAL,
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_change(user, **data: Any) -> Change:
        forbidden = {
            "assigned_to",
            "status",
            "risk_level",
            "id",
            "pk",
            "created_at",
            "updated_at",
        }
        for key in list(data.keys()):
            if key in forbidden:
                data.pop(key)

        change = Change.objects.create(requested_by=user, **data)

        ChangeHistory.record(
            change=change,
            event_type=ChangeHistory.EVENT_CREATED,
            user=user,
            comment="Change created.",
        )

        return change

    # ==========================================================
    # Internal transition helper
    # ==========================================================

    @staticmethod
    def _transition(
        change: Change,
        new_status: str,
        event_type: str,
        user=None,
        comment: str = "",
    ) -> Change:

        current = change.status
        allowed = ChangeService.STATUS_FLOW.get(current, [])

        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move a change from {current} to {new_status}."
            )

        change.status = new_status
        change.save(update_fields=["status", "updated_at"])

        ChangeHistory.record(
            change=change,
            event_type=event_type,
            user=user,
            old_value=current,
            new_value=new_status,
            comment=comment,
        )

        return change

    @staticmethod
    def _assert_may_implement(change: Change, user) -> None:
        """
        Only the assigned implementer, a manager or an administrator
        may advance implementation/validation/failure/rollback —
        enforced here so it cannot be bypassed by any call site that
        only checks change_change.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None:
            raise ValidationError("An acting user is required.")

        if is_administrator(user) or is_manager(user):
            return

        if change.assigned_to_id is None or change.assigned_to_id != user.pk:
            raise ValidationError(
                "Only the assigned implementer can update this change."
            )

    # ==========================================================
    # Submission and assessment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def submit_change(change: Change, user=None) -> Change:
        return ChangeService._transition(
            change,
            Change.STATUS_SUBMITTED,
            ChangeHistory.EVENT_SUBMITTED,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def assess_change(
        change: Change,
        user,
        impact: str,
        urgency: str,
    ) -> Change:

        if impact not in dict(Change.IMPACT_CHOICES):
            raise ValidationError("Invalid impact.")

        if urgency not in dict(Change.URGENCY_CHOICES):
            raise ValidationError("Invalid urgency.")

        if change.status != Change.STATUS_SUBMITTED:
            raise ValidationError(
                "Only a submitted change can be assessed."
            )

        risk_level = ChangeService.RISK_MATRIX[(impact, urgency)]

        change.impact = impact
        change.urgency = urgency
        change.risk_level = risk_level
        change.save(
            update_fields=["impact", "urgency", "risk_level", "updated_at"]
        )

        return ChangeService._transition(
            change,
            Change.STATUS_ASSESSED,
            ChangeHistory.EVENT_ASSESSED,
            user=user,
            comment=f"Risk assessed as {risk_level}.",
        )

    # ==========================================================
    # Approval
    # ==========================================================

    @staticmethod
    def _assert_may_decide(change: Change, approver) -> None:
        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if approver is None or not (
            is_administrator(approver) or is_manager(approver)
        ):
            raise ValidationError(
                "Only a manager or an administrator can approve or "
                "reject a change."
            )

        conflicted = {
            uid
            for uid in (change.requested_by_id, change.assigned_to_id)
            if uid is not None
        }

        if approver.pk in conflicted:
            raise ValidationError(
                "You cannot approve or reject a change you requested "
                "or are assigned to implement (separation of duties)."
            )

    @staticmethod
    @transaction.atomic
    def approve_change(
        change: Change,
        approver,
        comment: str = "",
    ) -> Change:

        if change.status != Change.STATUS_ASSESSED:
            raise ValidationError(
                "Only an assessed change can be approved."
            )

        ChangeService._assert_may_decide(change, approver)

        ChangeApproval.objects.create(
            change=change,
            actor=approver,
            decision=ChangeApproval.DECISION_APPROVED,
            comment=comment.strip(),
        )

        return ChangeService._transition(
            change,
            Change.STATUS_APPROVED,
            ChangeHistory.EVENT_APPROVED,
            user=approver,
            comment=comment.strip(),
        )

    @staticmethod
    @transaction.atomic
    def reject_change(
        change: Change,
        approver,
        comment: str,
    ) -> Change:

        if change.status not in (
            Change.STATUS_SUBMITTED,
            Change.STATUS_ASSESSED,
        ):
            raise ValidationError(
                "Only a submitted or assessed change can be rejected."
            )

        if not comment.strip():
            raise ValidationError(
                "A reason is required when rejecting a change."
            )

        ChangeService._assert_may_decide(change, approver)

        ChangeApproval.objects.create(
            change=change,
            actor=approver,
            decision=ChangeApproval.DECISION_REJECTED,
            comment=comment.strip(),
        )

        return ChangeService._transition(
            change,
            Change.STATUS_REJECTED,
            ChangeHistory.EVENT_REJECTED,
            user=approver,
            comment=comment.strip(),
        )

    # ==========================================================
    # Scheduling
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def schedule_change(change: Change, user, start, end) -> Change:

        if change.status != Change.STATUS_APPROVED:
            raise ValidationError(
                "Only an approved change can be scheduled."
            )

        if start is None or end is None or start >= end:
            raise ValidationError(
                "A schedule requires a start time before its end time."
            )

        if change.department_id is not None:
            from apps.service_desk.selectors.change_selector import (
                ChangeSelector,
            )

            conflicts = ChangeSelector.get_scheduled_conflicts(
                change.department_id,
                start,
                end,
                exclude_pk=change.pk,
            )

            if conflicts.exists():
                raise ValidationError(
                    "This schedule conflicts with another change "
                    "already scheduled for this department."
                )

        change.scheduled_start = start
        change.scheduled_end = end
        change.save(
            update_fields=["scheduled_start", "scheduled_end", "updated_at"]
        )

        return ChangeService._transition(
            change,
            Change.STATUS_SCHEDULED,
            ChangeHistory.EVENT_SCHEDULED,
            user=user,
        )

    # ==========================================================
    # Implementation
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def assign_change(change: Change, technician, user=None) -> Change:
        if technician is None:
            raise ValidationError("An implementer is required.")

        if not technician.is_active:
            raise ValidationError("That user is inactive.")

        previous = change.assigned_to

        change.assigned_to = technician
        change.save(update_fields=["assigned_to", "updated_at"])

        ChangeHistory.record(
            change=change,
            event_type=ChangeHistory.EVENT_ASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=technician.get_username(),
        )

        return change

    @staticmethod
    @transaction.atomic
    def start_implementation(change: Change, user=None) -> Change:
        ChangeService._assert_may_implement(change, user)
        return ChangeService._transition(
            change,
            Change.STATUS_IMPLEMENTING,
            ChangeHistory.EVENT_IMPLEMENTING,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def request_validation(change: Change, user=None) -> Change:
        ChangeService._assert_may_implement(change, user)
        return ChangeService._transition(
            change,
            Change.STATUS_VALIDATION,
            ChangeHistory.EVENT_VALIDATION,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def complete_change(change: Change, user=None) -> Change:
        ChangeService._assert_may_implement(change, user)
        return ChangeService._transition(
            change,
            Change.STATUS_COMPLETED,
            ChangeHistory.EVENT_COMPLETED,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def fail_change(change: Change, user, reason: str) -> Change:
        if not reason.strip():
            raise ValidationError(
                "A reason is required when failing a change."
            )

        ChangeService._assert_may_implement(change, user)

        return ChangeService._transition(
            change,
            Change.STATUS_FAILED,
            ChangeHistory.EVENT_FAILED,
            user=user,
            comment=reason.strip(),
        )

    @staticmethod
    @transaction.atomic
    def rollback_change(change: Change, user, reason: str) -> Change:
        if not reason.strip():
            raise ValidationError(
                "A reason is required when rolling back a change."
            )

        ChangeService._assert_may_implement(change, user)

        return ChangeService._transition(
            change,
            Change.STATUS_ROLLED_BACK,
            ChangeHistory.EVENT_ROLLED_BACK,
            user=user,
            comment=reason.strip(),
        )

    # ==========================================================
    # Comments
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_comment(change: Change, comment: str, user=None) -> ChangeHistory:
        if not comment.strip():
            raise ValidationError("Comment cannot be empty.")

        return ChangeHistory.record(
            change=change,
            event_type=ChangeHistory.EVENT_COMMENT,
            user=user,
            comment=comment.strip(),
        )
