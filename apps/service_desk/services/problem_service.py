from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.service_desk.models import (
    Problem,
    ProblemHistory,
    RootCauseAnalysis,
    Ticket,
)

User = get_user_model()


class ProblemService:
    """
    Enterprise Service Desk problem business service.
    """

    STATUS_FLOW = {
        "open": ["investigating"],
        "investigating": ["known_error", "resolved"],
        "known_error": ["resolved"],
        "resolved": ["closed"],
        "closed": ["open"],
    }

    # ==========================================================
    # Create
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_problem(**data: Any) -> Problem:
        user = data.get("created_by")

        problem = Problem.objects.create(**data)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_CREATED,
            user=user,
            comment="Problem created.",
            to_status=problem.status,
        )

        return problem

    # ==========================================================
    # Update
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def update_problem(problem: Problem, user=None, **fields) -> Problem:

        changed = {}

        for field, value in fields.items():

            if not hasattr(problem, field):
                continue

            current = getattr(problem, field)

            if current != value:
                changed[field] = (current, value)
                setattr(problem, field, value)

        if not changed:
            return problem

        problem.full_clean()
        problem.save()

        for field, values in changed.items():

            ProblemHistory.record(
                problem=problem,
                event_type=ProblemHistory.EVENT_UPDATED,
                user=user,
                old_value=str(values[0]),
                new_value=str(values[1]),
                comment=f"{field} updated.",
            )

        return problem

    # ==========================================================
    # Assignment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def assign_problem(
        problem: Problem,
        investigator: User,
        user=None,
    ) -> Problem:

        if investigator is None:
            raise ValidationError("Investigator is required.")

        if not investigator.is_active:
            raise ValidationError("Investigator is inactive.")

        problem.assigned_to = investigator
        problem.save(update_fields=["assigned_to", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_ASSIGNED,
            user=user,
            new_value=investigator.get_username(),
        )

        return problem

    @staticmethod
    @transaction.atomic
    def unassign_problem(problem: Problem, user=None) -> Problem:

        previous = problem.assigned_to

        problem.assigned_to = None
        problem.save(update_fields=["assigned_to", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UNASSIGNED,
            user=user,
            old_value=str(previous) if previous else "",
        )

        return problem

    # ==========================================================
    # Status
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def change_status(
        problem: Problem,
        status: str,
        user=None,
    ) -> Problem:

        status = status.lower()

        if status not in dict(Problem.STATUS_CHOICES):
            raise ValidationError("Invalid status.")

        current = problem.status

        if current == status:
            return problem

        allowed = ProblemService.STATUS_FLOW.get(current, [])

        if status not in allowed:
            raise ValidationError(
                f"Cannot move from {current} to {status}."
            )

        history_comment = ""

        if status == "known_error":
            ProblemService._require_known_error_ready(problem)
            problem.is_known_error = True

        if status == "investigating":
            created = ProblemService._ensure_root_cause_analysis(problem)

            if created:
                history_comment = "Root Cause Analysis initialized."

        problem.status = status

        update_fields = ["status", "updated_at"]

        if status == "known_error":
            update_fields.append("is_known_error")

        problem.save(update_fields=update_fields)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_STATUS_CHANGED,
            user=user,
            from_status=current,
            to_status=status,
            comment=history_comment,
        )

        return problem

    # ==========================================================
    # Root Cause Analysis
    # ==========================================================

    @staticmethod
    def _ensure_root_cause_analysis(problem: Problem) -> bool:
        """
        Create the problem's RootCauseAnalysis if one does not
        already exist. Returns True if a new record was created.

        A Problem owns exactly one RootCauseAnalysis (ADR-009);
        the OneToOneField uniqueness constraint backs this up at
        the database level.
        """

        _, created = RootCauseAnalysis.objects.get_or_create(
            problem=problem,
            defaults={
                "status": "draft",
                "owner": problem.assigned_to,
                "problem_statement": (
                    problem.description or problem.title
                ),
            },
        )

        return created

    @staticmethod
    def _require_known_error_ready(problem: Problem) -> None:

        rca = getattr(problem, "rca", None)

        if rca is None:
            raise ValidationError(
                "A Root Cause Analysis is required before "
                "marking a Known Error."
            )

        if not problem.root_cause.strip():
            raise ValidationError(
                "Root cause must be recorded before marking "
                "a Known Error."
            )

    @staticmethod
    @transaction.atomic
    def mark_known_error(problem: Problem, user=None) -> Problem:

        ProblemService._require_known_error_ready(problem)

        if problem.is_known_error:
            return problem

        problem.is_known_error = True
        problem.save(update_fields=["is_known_error", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_KNOWN_ERROR_DECLARED,
            user=user,
        )

        return problem

    @staticmethod
    @transaction.atomic
    @staticmethod
    def record_root_cause(
        problem: Problem,
        root_cause: str,
        user=None,
    ) -> Problem:

        if not root_cause.strip():
            raise ValidationError("Root cause cannot be empty.")

        previous = problem.root_cause
        value = root_cause.strip()

        # Ensure every Problem has its dedicated RCA record.
        ProblemService._ensure_root_cause_analysis(problem)

        # Problem.root_cause remains the value rendered by the
        # existing Problem detail template.
        problem.root_cause = value
        problem.save(update_fields=["root_cause", "updated_at"])

        # Keep the dedicated RCA record synchronized with the
        # Problem-level root cause.
        rca = RootCauseAnalysis.objects.get(problem=problem)
        rca.problem_statement = value
        rca.save(update_fields=["problem_statement", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_ROOT_CAUSE_UPDATED,
            user=user,
            old_value=previous,
            new_value=problem.root_cause,
        )

        return problem
    @staticmethod
    @transaction.atomic
    def record_workaround(
        problem: Problem,
        workaround: str,
        user=None,
    ) -> Problem:

        if not workaround.strip():
            raise ValidationError("Workaround cannot be empty.")

        previous = problem.workaround

        problem.workaround = workaround.strip()
        problem.save(update_fields=["workaround", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_WORKAROUND_UPDATED,
            user=user,
            old_value=previous,
            new_value=problem.workaround,
        )

        return problem

    # ==========================================================
    # Ticket Linking
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def link_ticket(
        problem: Problem,
        ticket: Ticket,
        user=None,
    ) -> Problem:

        if problem.related_tickets.filter(pk=ticket.pk).exists():
            raise ValidationError(
                "Ticket is already linked to this problem."
            )

        problem.related_tickets.add(ticket)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_TICKET_LINKED,
            user=user,
            new_value=str(ticket),
        )

        return problem

    @staticmethod
    @transaction.atomic
    def unlink_ticket(
        problem: Problem,
        ticket: Ticket,
        user=None,
    ) -> Problem:

        if not problem.related_tickets.filter(pk=ticket.pk).exists():
            raise ValidationError(
                "Ticket is not linked to this problem."
            )

        problem.related_tickets.remove(ticket)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_TICKET_UNLINKED,
            user=user,
            old_value=str(ticket),
        )

        return problem

    # ==========================================================
    # Comments
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def add_comment(
        problem: Problem,
        comment: str,
        user=None,
    ) -> ProblemHistory:

        if not comment.strip():
            raise ValidationError("Comment cannot be empty.")

        return ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_COMMENT,
            user=user,
            comment=comment.strip(),
        )

    # ==========================================================
    # Close
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def close_problem(
        problem: Problem,
        user=None,
    ) -> Problem:

        if problem.status != "resolved":
            raise ValidationError(
                "Only resolved problems can be closed."
            )

        return ProblemService.change_status(
            problem,
            "closed",
            user=user,
        )

    # ==========================================================
    # Reopen
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def reopen_problem(
        problem: Problem,
        user=None,
    ) -> Problem:

        if problem.status != "closed":
            raise ValidationError(
                "Only closed problems can be reopened."
            )

        return ProblemService.change_status(
            problem,
            "open",
            user=user,
        )

    # ==========================================================
    # Delete
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def delete_problem(problem: Problem) -> None:
        problem.delete()
