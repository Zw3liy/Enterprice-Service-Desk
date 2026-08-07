from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.service_desk.models import Problem, Ticket


class ProblemSelector:
    """
    Read-only data access layer for Problem queries.

    This class contains optimized queries only.
    No business logic or write operations should exist here.
    """

    _STOPWORDS = {
        "the", "and", "for", "with", "from", "this", "that",
        "have", "has", "was", "were", "are", "not", "but",
        "into", "onto", "when", "then", "than", "which",
    }

    @staticmethod
    def _base_queryset() -> QuerySet[Problem]:
        """
        Base optimized queryset used by all selectors.
        """
        return (
            Problem.objects.select_related(
                "department",
                "created_by",
                "assigned_to",
                "rca",
            )
            .prefetch_related("related_tickets", "history")
            .order_by("-created_at")
        )

    @classmethod
    def get_by_id(cls, problem_id: int) -> Problem:
        """
        Retrieve a single problem by primary key.

        Raises:
            Problem.DoesNotExist
        """
        return cls._base_queryset().get(pk=problem_id)

    @classmethod
    def get_by_status(cls, status: str) -> QuerySet[Problem]:
        """
        Retrieve problems by status.
        """
        return cls._base_queryset().filter(status=status)

    @classmethod
    def get_by_priority(cls, priority: str) -> QuerySet[Problem]:
        """
        Retrieve problems by priority.
        """
        return cls._base_queryset().filter(priority=priority)

    @classmethod
    def get_by_department(cls, department_id: int) -> QuerySet[Problem]:
        """
        Retrieve problems belonging to a department.
        """
        return cls._base_queryset().filter(department_id=department_id)

    @classmethod
    def get_by_assignee(cls, user_id: int) -> QuerySet[Problem]:
        """
        Retrieve problems assigned to an investigator.
        """
        return cls._base_queryset().filter(assigned_to_id=user_id)

    @classmethod
    def get_open_problems(cls) -> QuerySet[Problem]:
        """
        Retrieve all open problems.
        """
        return cls._base_queryset().filter(status="open")

    @classmethod
    def get_known_errors(cls) -> QuerySet[Problem]:
        """
        Retrieve all problems declared as Known Errors.
        """
        return cls._base_queryset().filter(is_known_error=True)

    @classmethod
    def get_recent_problems(cls, limit: int = 10) -> QuerySet[Problem]:
        """
        Retrieve most recently created problems.
        """
        return cls._base_queryset()[:limit]

    @classmethod
    def get_problems_for_ticket(cls, ticket: Ticket) -> QuerySet[Problem]:
        """
        Retrieve problems linked to a given ticket.
        """
        return cls._base_queryset().filter(related_tickets=ticket)

    @classmethod
    def search(cls, query: str) -> QuerySet[Problem]:
        """
        Full problem search.
        """
        return cls._base_queryset().filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(root_cause__icontains=query)
        )

    @classmethod
    def dashboard_statistics(cls) -> dict[str, Any]:
        """
        Dashboard metrics and trend analysis.
        """
        queryset = Problem.objects.all()

        stats = queryset.aggregate(
            total_problems=Count("id"),
            open_problems=Count(
                "id",
                filter=Q(status="open"),
            ),
            investigating_problems=Count(
                "id",
                filter=Q(status="investigating"),
            ),
            known_error_problems=Count(
                "id",
                filter=Q(is_known_error=True),
            ),
            resolved_problems=Count(
                "id",
                filter=Q(status="resolved"),
            ),
            closed_problems=Count(
                "id",
                filter=Q(status="closed"),
            ),
        )

        stats["problems_by_priority"] = dict(
            queryset.values_list("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )

        stats["problems_by_department"] = dict(
            queryset.filter(department__isnull=False)
            .values_list("department__name")
            .annotate(count=Count("id"))
            .order_by("department__name")
        )

        resolution_duration = ExpressionWrapper(
            F("updated_at") - F("created_at"),
            output_field=DurationField(),
        )

        stats["average_resolution_time"] = (
            queryset.filter(status__in=["resolved", "closed"])
            .annotate(resolution_duration=resolution_duration)
            .aggregate(average=Avg("resolution_duration"))["average"]
        )

        since = timezone.now() - timedelta(days=180)

        growth = (
            queryset.filter(created_at__gte=since)
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

        stats["problem_growth_trend"] = list(growth)

        return stats

    @classmethod
    def repeat_incident_detection(
        cls,
        problem: Problem,
        limit: int = 10,
    ) -> QuerySet[Ticket]:
        """
        Rank existing tickets as repeat-incident candidates for a
        problem.

        The Ticket model (apps/service_desk/models/ticket.py) has
        no Configuration Item, signature, or error-message field,
        so this uses the closest available signals instead:
        department, category (request_type via select_related for
        later display), and free-text overlap across
        title/description/tags. Candidates already linked to the
        problem are excluded.
        """

        already_linked = problem.related_tickets.values_list(
            "pk", flat=True
        )

        candidates = (
            Ticket.objects.select_related(
                "department",
                "request_type",
                "assigned_to",
                "created_by",
            )
            .exclude(pk__in=already_linked)
        )

        if problem.department_id:
            candidates = candidates.filter(
                department_id=problem.department_id
            )

        keywords = cls._extract_keywords(
            problem.title,
            problem.description,
        )

        if not keywords:
            return candidates.order_by("-created_at")[:limit]

        text_filter = Q()
        match_score = Value(0, output_field=IntegerField())

        for keyword in keywords:
            keyword_match = (
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(tags__icontains=keyword)
            )

            text_filter |= keyword_match

            match_score = match_score + Case(
                When(keyword_match, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )

        return (
            candidates.filter(text_filter)
            .annotate(match_score=match_score)
            .order_by("-match_score", "-created_at")[:limit]
        )

    @classmethod
    def _extract_keywords(
        cls,
        *texts: str,
        limit: int = 8,
    ) -> list[str]:
        """
        Derive a small, bounded set of matchable keywords from
        free text, so repeat-incident lookups stay a single
        filtered query instead of scanning unbounded text.
        """

        words: set[str] = set()

        for text in texts:

            if not text:
                continue

            for raw_word in text.lower().split():

                cleaned = "".join(
                    char for char in raw_word if char.isalnum()
                )

                if len(cleaned) < 4:
                    continue

                if cleaned in cls._STOPWORDS:
                    continue

                words.add(cleaned)

        return sorted(words)[:limit]
