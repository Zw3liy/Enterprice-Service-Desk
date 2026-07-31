"""Release management services."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.release_management.models import Release, ReleaseTask
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ReleaseService:
    @classmethod
    @transaction.atomic
    def create_release(
        cls,
        company,
        *,
        name: str,
        version: str,
        description: str = "",
        manager=None,
        planned_start=None,
        planned_end=None,
        change_ids: list | None = None,
        actor=None,
    ) -> Release:
        release = Release.objects.create(
            company=company,
            name=name,
            version=version,
            description=description,
            manager=manager,
            planned_start=planned_start,
            planned_end=planned_end,
        )
        if change_ids:
            release.changes.set(change_ids)
        for seq, title in [
            (10, "Build artifacts"),
            (20, "QA sign-off"),
            (30, "CAB approval check"),
            (40, "Production deployment"),
            (50, "Post-deployment validation"),
        ]:
            ReleaseTask.objects.create(release=release, title=title, sequence=seq)
        AuditService.log(
            action="release.created",
            company=company,
            actor=actor,
            message=f"Release {version} created",
            object_type="release",
            object_id=str(release.pk),
        )
        return release

    @classmethod
    def transition(cls, release: Release, state: str, actor=None) -> Release:
        release.state = state
        if state == Release.State.DEPLOYING and not release.actual_start:
            release.actual_start = timezone.now()
        if state in {Release.State.DEPLOYED, Release.State.FAILED, Release.State.CANCELLED}:
            release.actual_end = timezone.now()
        release.save()
        AuditService.log(
            action="release.transition",
            company=release.company,
            actor=actor,
            message=f"Release {release.version} → {state}",
            object_type="release",
            object_id=str(release.pk),
        )
        return release

    @staticmethod
    def complete_task(task: ReleaseTask, actor=None) -> ReleaseTask:
        task.state = ReleaseTask.State.DONE
        if actor and not task.assignee_id:
            task.assignee = actor
        task.save()
        return task
