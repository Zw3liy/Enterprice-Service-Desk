from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import Release, ReleaseApproval, ReleaseHistory


class ReleaseService:
    """
    Release Management business service.

    A ``Change`` may only be linked to a ``Release`` once it has
    cleared CAB approval (``Release.CHANGE_ELIGIBLE_STATUSES``) — the
    mission's "approved eligibility boundary" requirement, enforced
    here rather than left to the UI to filter.
    """

    STATUS_FLOW = {
        Release.STATUS_DRAFT: [Release.STATUS_APPROVED],
        Release.STATUS_APPROVED: [Release.STATUS_SCHEDULED],
        Release.STATUS_SCHEDULED: [Release.STATUS_DEPLOYING],
        Release.STATUS_DEPLOYING: [
            Release.STATUS_VALIDATION,
            Release.STATUS_FAILED,
        ],
        Release.STATUS_VALIDATION: [
            Release.STATUS_COMPLETED,
            Release.STATUS_FAILED,
        ],
        Release.STATUS_FAILED: [Release.STATUS_ROLLED_BACK],
        Release.STATUS_COMPLETED: [],
        Release.STATUS_ROLLED_BACK: [],
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_release(user, **data: Any) -> Release:
        forbidden = {"status", "owner", "id", "pk", "created_at", "updated_at"}
        for key in list(data.keys()):
            if key in forbidden:
                data.pop(key)

        release = Release.objects.create(owner=user, **data)

        ReleaseHistory.record(
            release=release,
            event_type=ReleaseHistory.EVENT_CREATED,
            user=user,
            comment="Release created.",
        )

        return release

    # ==========================================================
    # Internal helpers
    # ==========================================================

    @staticmethod
    def _transition(
        release: Release,
        new_status: str,
        event_type: str,
        user=None,
        comment: str = "",
    ) -> Release:

        current = release.status
        allowed = ReleaseService.STATUS_FLOW.get(current, [])

        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move a release from {current} to {new_status}."
            )

        release.status = new_status
        release.save(update_fields=["status", "updated_at"])

        ReleaseHistory.record(
            release=release,
            event_type=event_type,
            user=user,
            old_value=current,
            new_value=new_status,
            comment=comment,
        )

        return release

    @staticmethod
    def _assert_may_operate(release: Release, user) -> None:
        """
        Only the owner, a manager or an administrator may advance
        deployment/validation/failure/rollback.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None:
            raise ValidationError("An acting user is required.")

        if is_administrator(user) or is_manager(user):
            return

        if release.owner_id is None or release.owner_id != user.pk:
            raise ValidationError(
                "Only the release owner can update this release."
            )

    # ==========================================================
    # Approval
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def approve_release(
        release: Release,
        approver,
        comment: str = "",
    ) -> Release:

        if release.status != Release.STATUS_DRAFT:
            raise ValidationError("Only a draft release can be approved.")

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if approver is None or not (
            is_administrator(approver) or is_manager(approver)
        ):
            raise ValidationError(
                "Only a manager or an administrator can approve a release."
            )

        if release.owner_id is not None and release.owner_id == approver.pk:
            raise ValidationError(
                "You cannot approve a release you own."
            )

        ReleaseApproval.objects.create(
            release=release,
            actor=approver,
            decision=ReleaseApproval.DECISION_APPROVED,
            comment=comment.strip(),
        )

        return ReleaseService._transition(
            release,
            Release.STATUS_APPROVED,
            ReleaseHistory.EVENT_APPROVED,
            user=approver,
            comment=comment.strip(),
        )

    # ==========================================================
    # Change linking (approved eligibility boundary)
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def link_change(release: Release, change, user=None) -> Release:
        if change.status not in Release.CHANGE_ELIGIBLE_STATUSES:
            raise ValidationError(
                "This change has not cleared CAB approval and cannot "
                "be linked to a release."
            )

        release.changes.add(change)

        ReleaseHistory.record(
            release=release,
            event_type=ReleaseHistory.EVENT_CHANGE_LINKED,
            user=user,
            new_value=str(change),
        )

        return release

    @staticmethod
    @transaction.atomic
    def unlink_change(release: Release, change, user=None) -> Release:
        release.changes.remove(change)

        ReleaseHistory.record(
            release=release,
            event_type=ReleaseHistory.EVENT_CHANGE_UNLINKED,
            user=user,
            old_value=str(change),
        )

        return release

    # ==========================================================
    # Ownership
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def assign_owner(release: Release, new_owner, user=None) -> Release:
        if new_owner is None or not new_owner.is_active:
            raise ValidationError("A valid, active owner is required.")

        previous = release.owner

        release.owner = new_owner
        release.save(update_fields=["owner", "updated_at"])

        ReleaseHistory.record(
            release=release,
            event_type=ReleaseHistory.EVENT_OWNER_ASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=new_owner.get_username(),
        )

        return release

    # ==========================================================
    # Scheduling
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def schedule_release(release: Release, user, start, end) -> Release:
        if release.status != Release.STATUS_APPROVED:
            raise ValidationError("Only an approved release can be scheduled.")

        if start is None or end is None or start >= end:
            raise ValidationError(
                "A schedule requires a start time before its end time."
            )

        if release.department_id is not None:
            from apps.service_desk.selectors.release_selector import (
                ReleaseSelector,
            )

            conflicts = ReleaseSelector.get_scheduled_conflicts(
                release.department_id,
                release.environment,
                start,
                end,
                exclude_pk=release.pk,
            )

            if conflicts.exists():
                raise ValidationError(
                    "This schedule conflicts with another release "
                    "already scheduled for this department and "
                    "environment."
                )

        release.scheduled_start = start
        release.scheduled_end = end
        release.save(
            update_fields=["scheduled_start", "scheduled_end", "updated_at"]
        )

        return ReleaseService._transition(
            release,
            Release.STATUS_SCHEDULED,
            ReleaseHistory.EVENT_SCHEDULED,
            user=user,
        )

    # ==========================================================
    # Deployment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def start_deployment(release: Release, user=None) -> Release:
        ReleaseService._assert_may_operate(release, user)
        return ReleaseService._transition(
            release,
            Release.STATUS_DEPLOYING,
            ReleaseHistory.EVENT_DEPLOYING,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def request_validation(release: Release, user=None) -> Release:
        ReleaseService._assert_may_operate(release, user)
        return ReleaseService._transition(
            release,
            Release.STATUS_VALIDATION,
            ReleaseHistory.EVENT_VALIDATION,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def complete_release(release: Release, user=None, outcome: str = "") -> Release:
        ReleaseService._assert_may_operate(release, user)

        if outcome.strip():
            release.outcome = outcome.strip()
            release.save(update_fields=["outcome", "updated_at"])

        return ReleaseService._transition(
            release,
            Release.STATUS_COMPLETED,
            ReleaseHistory.EVENT_COMPLETED,
            user=user,
            comment=outcome.strip(),
        )

    @staticmethod
    @transaction.atomic
    def fail_release(release: Release, user, reason: str) -> Release:
        if not reason.strip():
            raise ValidationError("A reason is required when failing a release.")

        ReleaseService._assert_may_operate(release, user)

        release.outcome = reason.strip()
        release.save(update_fields=["outcome", "updated_at"])

        return ReleaseService._transition(
            release,
            Release.STATUS_FAILED,
            ReleaseHistory.EVENT_FAILED,
            user=user,
            comment=reason.strip(),
        )

    @staticmethod
    @transaction.atomic
    def rollback_release(release: Release, user, reason: str) -> Release:
        if not reason.strip():
            raise ValidationError(
                "A reason is required when rolling back a release."
            )

        ReleaseService._assert_may_operate(release, user)

        return ReleaseService._transition(
            release,
            Release.STATUS_ROLLED_BACK,
            ReleaseHistory.EVENT_ROLLED_BACK,
            user=user,
            comment=reason.strip(),
        )

    # ==========================================================
    # Comments
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_comment(release: Release, comment: str, user=None) -> ReleaseHistory:
        if not comment.strip():
            raise ValidationError("Comment cannot be empty.")

        return ReleaseHistory.record(
            release=release,
            event_type=ReleaseHistory.EVENT_COMMENT,
            user=user,
            comment=comment.strip(),
        )
