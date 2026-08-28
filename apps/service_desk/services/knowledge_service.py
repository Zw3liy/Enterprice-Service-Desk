from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.service_desk.models import (
    KnowledgeArticle,
    KnowledgeArticleHistory,
    KnowledgeFeedback,
)


class KnowledgeService:
    """
    Knowledge Management business service.

    Publication and review are governance actions: a reviewer may
    never approve or send back their own article (self-review
    prevention, mirroring the separation-of-duties pattern used by
    Change/Release/Service Request approvals throughout this
    program).
    """

    STATUS_FLOW = {
        KnowledgeArticle.STATUS_DRAFT: [KnowledgeArticle.STATUS_IN_REVIEW],
        KnowledgeArticle.STATUS_IN_REVIEW: [
            KnowledgeArticle.STATUS_APPROVED,
            KnowledgeArticle.STATUS_DRAFT,
        ],
        KnowledgeArticle.STATUS_APPROVED: [KnowledgeArticle.STATUS_PUBLISHED],
        KnowledgeArticle.STATUS_PUBLISHED: [
            KnowledgeArticle.STATUS_ARCHIVED,
            KnowledgeArticle.STATUS_DRAFT,
        ],
        KnowledgeArticle.STATUS_ARCHIVED: [KnowledgeArticle.STATUS_DRAFT],
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_article(user, **data: Any) -> KnowledgeArticle:
        forbidden = {
            "author",
            "reviewer",
            "status",
            "version",
            "published_at",
            "id",
            "pk",
            "created_at",
            "updated_at",
        }
        for key in list(data.keys()):
            if key in forbidden:
                data.pop(key)

        article = KnowledgeArticle.objects.create(author=user, **data)

        KnowledgeArticleHistory.record(
            article=article,
            event_type=KnowledgeArticleHistory.EVENT_CREATED,
            user=user,
            comment="Article created.",
        )

        return article

    @staticmethod
    @transaction.atomic
    def update_article(article: KnowledgeArticle, user=None, **fields: Any) -> KnowledgeArticle:
        changed = {}

        for field, value in fields.items():
            if field in {"author", "reviewer", "status", "version", "published_at"}:
                continue

            if not hasattr(article, field):
                continue

            current = getattr(article, field)
            if current != value:
                changed[field] = value
                setattr(article, field, value)

        if not changed:
            return article

        article.full_clean()
        article.save()
        return article

    # ==========================================================
    # Internal helpers
    # ==========================================================

    @staticmethod
    def _transition(
        article: KnowledgeArticle,
        new_status: str,
        event_type: str,
        user=None,
        comment: str = "",
    ) -> KnowledgeArticle:

        current = article.status
        allowed = KnowledgeService.STATUS_FLOW.get(current, [])

        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move an article from {current} to {new_status}."
            )

        article.status = new_status
        article.save(update_fields=["status", "updated_at"])

        KnowledgeArticleHistory.record(
            article=article,
            event_type=event_type,
            user=user,
            old_value=current,
            new_value=new_status,
            comment=comment,
        )

        return article

    @staticmethod
    def _assert_may_author(article: KnowledgeArticle, user) -> None:
        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None:
            raise ValidationError("An acting user is required.")

        if is_administrator(user) or is_manager(user):
            return

        if article.author_id is None or article.author_id != user.pk:
            raise ValidationError(
                "Only the article's author can perform this action."
            )

    @staticmethod
    def _assert_may_review(article: KnowledgeArticle, user) -> None:
        """
        Separation of duties: the acting reviewer may not be the
        article's author. A manager/administrator may review any
        article they didn't author themselves; otherwise the actor
        must be the assigned reviewer.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None:
            raise ValidationError("An acting user is required.")

        if article.author_id is not None and article.author_id == user.pk:
            raise ValidationError(
                "You cannot review or approve your own article."
            )

        if is_administrator(user) or is_manager(user):
            return

        if article.reviewer_id is None or article.reviewer_id != user.pk:
            raise ValidationError(
                "Only the assigned reviewer can decide this article."
            )

    # ==========================================================
    # Review workflow
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def submit_for_review(article: KnowledgeArticle, user=None) -> KnowledgeArticle:
        KnowledgeService._assert_may_author(article, user)
        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_IN_REVIEW,
            KnowledgeArticleHistory.EVENT_SUBMITTED,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def assign_reviewer(article: KnowledgeArticle, reviewer, user=None) -> KnowledgeArticle:
        if reviewer is None or not reviewer.is_active:
            raise ValidationError("A valid, active reviewer is required.")

        if article.author_id is not None and article.author_id == reviewer.pk:
            raise ValidationError(
                "The author cannot also be the reviewer."
            )

        previous = article.reviewer

        article.reviewer = reviewer
        article.save(update_fields=["reviewer", "updated_at"])

        KnowledgeArticleHistory.record(
            article=article,
            event_type=KnowledgeArticleHistory.EVENT_REVIEWER_ASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
            new_value=reviewer.get_username(),
        )

        return article

    @staticmethod
    @transaction.atomic
    def approve_article(article: KnowledgeArticle, user, comment: str = "") -> KnowledgeArticle:
        if article.status != KnowledgeArticle.STATUS_IN_REVIEW:
            raise ValidationError("Only an article in review can be approved.")

        KnowledgeService._assert_may_review(article, user)

        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_APPROVED,
            KnowledgeArticleHistory.EVENT_APPROVED,
            user=user,
            comment=comment.strip(),
        )

    @staticmethod
    @transaction.atomic
    def send_back(article: KnowledgeArticle, user, comment: str) -> KnowledgeArticle:
        if not comment.strip():
            raise ValidationError(
                "Revision notes are required when sending an article back."
            )

        if article.status != KnowledgeArticle.STATUS_IN_REVIEW:
            raise ValidationError("Only an article in review can be sent back.")

        KnowledgeService._assert_may_review(article, user)

        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_DRAFT,
            KnowledgeArticleHistory.EVENT_SENT_BACK,
            user=user,
            comment=comment.strip(),
        )

    # ==========================================================
    # Publication
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def publish_article(article: KnowledgeArticle, user=None) -> KnowledgeArticle:
        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None or not (is_administrator(user) or is_manager(user)):
            raise ValidationError(
                "Only a manager or an administrator can publish an article."
            )

        article.version += 1
        article.published_at = timezone.now()
        article.save(update_fields=["version", "published_at", "updated_at"])

        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_PUBLISHED,
            KnowledgeArticleHistory.EVENT_PUBLISHED,
            user=user,
            comment=f"Published as version {article.version}.",
        )

    @staticmethod
    @transaction.atomic
    def archive_article(article: KnowledgeArticle, user=None) -> KnowledgeArticle:
        KnowledgeService._assert_may_author(article, user)
        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_ARCHIVED,
            KnowledgeArticleHistory.EVENT_ARCHIVED,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def start_revision(article: KnowledgeArticle, user=None) -> KnowledgeArticle:
        KnowledgeService._assert_may_author(article, user)
        return KnowledgeService._transition(
            article,
            KnowledgeArticle.STATUS_DRAFT,
            KnowledgeArticleHistory.EVENT_REVISION_STARTED,
            user=user,
        )

    # ==========================================================
    # Feedback
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def submit_feedback(
        article: KnowledgeArticle,
        user,
        is_helpful: bool,
    ) -> KnowledgeFeedback:
        if article.status != KnowledgeArticle.STATUS_PUBLISHED:
            raise ValidationError(
                "Feedback can only be left on a published article."
            )

        feedback, _created = KnowledgeFeedback.objects.update_or_create(
            article=article,
            user=user,
            defaults={"is_helpful": is_helpful},
        )

        return feedback
