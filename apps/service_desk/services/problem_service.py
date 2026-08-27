from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from django.utils import timezone

from apps.service_desk.models import (
    Action,
    Approval,
    Evidence,
    FishboneFactor,
    FiveWhys,
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
    def record_root_cause(
        problem: Problem,
        root_cause: str,
        user=None,
    ) -> Problem:

        if not root_cause.strip():
            raise ValidationError("Root cause cannot be empty.")

        previous = problem.root_cause

        problem.root_cause = root_cause.strip()
        problem.save(update_fields=["root_cause", "updated_at"])

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
    # RCA authoring — Five Whys, Fishbone, Evidence, CAPA, Approval
    #
    # These five models existed and were rendered read-only by the
    # Problem UI: there was no way to create one outside the Django
    # admin. Every mutation below goes through this service so the
    # audit trail, the state rules and the RCA's own status can never
    # be bypassed by a view writing to the model directly.
    # ==========================================================

    CLOSED_RCA_STATUSES = {"approved", "rejected"}

    @staticmethod
    def get_or_create_rca(problem: Problem, user=None) -> RootCauseAnalysis:
        """
        The problem's single RCA, creating it on first use.

        Normally created when the problem enters Investigating, but
        an investigator may start documenting before then.
        """

        created = ProblemService._ensure_root_cause_analysis(problem)

        problem.refresh_from_db()
        rca = problem.rca

        if created:
            ProblemHistory.record(
                problem=problem,
                event_type=ProblemHistory.EVENT_UPDATED,
                user=user,
                comment="Root Cause Analysis initialized.",
            )

        return rca

    @staticmethod
    def _assert_rca_open(rca: RootCauseAnalysis) -> None:
        """
        A signed-off RCA is evidence, not a working document.
        """

        if rca.status in ProblemService.CLOSED_RCA_STATUSES:
            raise ValidationError(
                "This Root Cause Analysis has been "
                f"{rca.get_status_display().lower()} and can no longer "
                "be edited."
            )

    @staticmethod
    def _touch_rca(rca: RootCauseAnalysis) -> None:
        """
        Draft RCAs become in-progress the moment real work lands.
        """

        if rca.status == "draft":
            rca.status = "in_progress"
            rca.save(update_fields=["status", "updated_at"])

    @staticmethod
    @transaction.atomic
    def update_rca(
        rca: RootCauseAnalysis,
        user=None,
        **fields,
    ) -> RootCauseAnalysis:
        """
        Update the RCA's own narrative fields and method.
        """

        ProblemService._assert_rca_open(rca)

        changed = []

        for field, value in fields.items():
            if not hasattr(rca, field):
                continue

            if getattr(rca, field) != value:
                setattr(rca, field, value)
                changed.append(field)

        if not changed:
            return rca

        rca.full_clean()
        rca.save()

        ProblemHistory.record(
            problem=rca.problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=f"RCA updated: {', '.join(sorted(changed))}.",
        )

        return rca

    # -- Five Whys --------------------------------------------------

    @staticmethod
    @transaction.atomic
    def add_five_whys_step(
        problem: Problem,
        question: str,
        answer: str,
        user=None,
        step_number: int | None = None,
    ) -> FiveWhys:
        """
        Append a "why" to the chain.

        The step number is allocated by the service rather than taken
        from the request, so a concurrent submission cannot collide
        with the model's unique (rca, step_number) constraint by
        guessing.
        """

        rca = ProblemService.get_or_create_rca(problem, user=user)

        ProblemService._assert_rca_open(rca)

        if not question.strip():
            raise ValidationError("The question cannot be empty.")

        if not answer.strip():
            raise ValidationError("The answer cannot be empty.")

        if step_number is None:
            last = rca.five_whys.order_by("-step_number").first()
            step_number = (last.step_number + 1) if last else 1

        if rca.five_whys.filter(step_number=step_number).exists():
            raise ValidationError(
                f"Step {step_number} already exists for this analysis."
            )

        step = FiveWhys.objects.create(
            rca=rca,
            step_number=step_number,
            question=question.strip(),
            answer=answer.strip(),
        )

        ProblemService._touch_rca(rca)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=f"Five Whys step {step_number} added.",
            new_value=step.answer,
            metadata={"five_whys_id": step.pk},
        )

        return step

    # -- Fishbone ---------------------------------------------------

    @staticmethod
    @transaction.atomic
    def add_fishbone_factor(
        problem: Problem,
        category: str,
        factor_description: str,
        user=None,
        is_root_cause: bool = False,
    ) -> FishboneFactor:

        rca = ProblemService.get_or_create_rca(problem, user=user)

        ProblemService._assert_rca_open(rca)

        if category not in dict(FishboneFactor.CATEGORY_CHOICES):
            raise ValidationError("Invalid fishbone category.")

        if not factor_description.strip():
            raise ValidationError("The factor description cannot be empty.")

        factor = FishboneFactor.objects.create(
            rca=rca,
            category=category,
            factor_description=factor_description.strip(),
            is_root_cause=is_root_cause,
        )

        ProblemService._touch_rca(rca)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=(
                f"Fishbone factor added ({factor.get_category_display()})."
            ),
            new_value=factor.factor_description,
            metadata={"fishbone_factor_id": factor.pk},
        )

        return factor

    @staticmethod
    @transaction.atomic
    def set_factor_as_root_cause(
        factor: FishboneFactor,
        user=None,
        is_root_cause: bool = True,
    ) -> FishboneFactor:

        ProblemService._assert_rca_open(factor.rca)

        if factor.is_root_cause == is_root_cause:
            return factor

        factor.is_root_cause = is_root_cause
        factor.save(update_fields=["is_root_cause"])

        ProblemHistory.record(
            problem=factor.rca.problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=(
                "Fishbone factor marked as root cause."
                if is_root_cause
                else "Fishbone factor no longer marked as root cause."
            ),
            metadata={"fishbone_factor_id": factor.pk},
        )

        return factor

    # -- Evidence ---------------------------------------------------

    @staticmethod
    @transaction.atomic
    def add_evidence(
        problem: Problem,
        title: str,
        file_or_link: str,
        user=None,
        description: str = "",
    ) -> Evidence:

        rca = ProblemService.get_or_create_rca(problem, user=user)

        ProblemService._assert_rca_open(rca)

        if not title.strip():
            raise ValidationError("Evidence needs a title.")

        if not file_or_link.strip():
            raise ValidationError("Evidence needs a file reference or link.")

        evidence = Evidence.objects.create(
            rca=rca,
            title=title.strip(),
            file_or_link=file_or_link.strip(),
            description=description.strip(),
        )

        ProblemService._touch_rca(rca)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=f"Evidence added: {evidence.title}.",
            metadata={"evidence_id": evidence.pk},
        )

        return evidence

    # -- Corrective / preventive actions ----------------------------

    @staticmethod
    @transaction.atomic
    def add_action(
        problem: Problem,
        action_type: str,
        description: str,
        due_date,
        user=None,
        assigned_to=None,
    ) -> Action:

        rca = ProblemService.get_or_create_rca(problem, user=user)

        ProblemService._assert_rca_open(rca)

        if action_type not in dict(Action.ACTION_TYPE_CHOICES):
            raise ValidationError("Invalid action type.")

        if not description.strip():
            raise ValidationError("The action description cannot be empty.")

        if due_date is None:
            raise ValidationError("A due date is required.")

        if assigned_to is not None and not assigned_to.is_active:
            raise ValidationError("Cannot assign an action to an inactive user.")

        action = Action.objects.create(
            rca=rca,
            action_type=action_type,
            description=description.strip(),
            due_date=due_date,
            assigned_to=assigned_to,
        )

        ProblemService._touch_rca(rca)

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=(
                f"{action.get_action_type_display()} action raised, "
                f"due {due_date}."
            ),
            metadata={"action_id": action.pk},
        )

        return action

    ACTION_STATUS_FLOW = {
        "open": ["in_progress", "cancelled"],
        "in_progress": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    }

    @staticmethod
    @transaction.atomic
    def change_action_status(
        action: Action,
        status: str,
        user=None,
    ) -> Action:
        """
        Move a CAPA through its own small lifecycle.

        Completed and cancelled are terminal: reopening an action
        would silently rewrite the record an approval was granted
        against.
        """

        if status not in dict(Action.STATUS_CHOICES):
            raise ValidationError("Invalid action status.")

        current = action.status

        if current == status:
            return action

        allowed = ProblemService.ACTION_STATUS_FLOW.get(current, [])

        if status not in allowed:
            raise ValidationError(
                f"Cannot move an action from {current} to {status}."
            )

        action.status = status
        action.save(update_fields=["status"])

        ProblemHistory.record(
            problem=action.rca.problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=f"Action {action.pk} moved to {status}.",
            old_value=current,
            new_value=status,
            metadata={"action_id": action.pk},
        )

        return action

    # -- Approvals --------------------------------------------------

    @staticmethod
    @transaction.atomic
    def request_approval(
        problem: Problem,
        approver,
        user=None,
    ) -> Approval:
        """
        Ask a named person to sign the investigation off.
        """

        rca = ProblemService.get_or_create_rca(problem, user=user)

        ProblemService._assert_rca_open(rca)

        if approver is None or not approver.is_active:
            raise ValidationError("A valid approver is required.")

        if rca.approvals.filter(
            approver=approver, status="pending"
        ).exists():
            raise ValidationError(
                "This approver already has a pending request."
            )

        if not problem.root_cause.strip():
            raise ValidationError(
                "Record the root cause before requesting sign-off."
            )

        approval = Approval.objects.create(
            rca=rca,
            approver=approver,
            status="pending",
        )

        if rca.status in ("draft", "in_progress"):
            rca.status = "completed"
            rca.save(update_fields=["status", "updated_at"])

        ProblemHistory.record(
            problem=problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=(
                f"RCA sign-off requested from "
                f"{approver.get_username()}."
            ),
            metadata={"approval_id": approval.pk},
        )

        ProblemService._notify_problem_update(
            problem,
            subject=f"RCA sign-off requested on problem #{problem.pk}",
            body=f"{problem.title} is ready for review.",
            actor=user,
        )

        return approval

    @staticmethod
    @transaction.atomic
    def decide_approval(
        approval: Approval,
        status: str,
        user=None,
        comments: str = "",
    ) -> Approval:
        """
        Record an approver's decision.

        Only the nominated approver may decide, and only once —
        enforced here so no view can bypass it.
        """

        if status not in ("approved", "rejected"):
            raise ValidationError("An approval is either approved or rejected.")

        if approval.status != "pending":
            raise ValidationError("This approval has already been decided.")

        if user is None or (
            approval.approver_id and approval.approver_id != user.pk
        ):
            raise ValidationError(
                "Only the nominated approver can decide this sign-off."
            )

        approval.status = status
        approval.comments = comments.strip()
        approval.decided_at = timezone.now()
        approval.save(
            update_fields=["status", "comments", "decided_at"]
        )

        rca = approval.rca
        rca.status = status
        rca.save(update_fields=["status", "updated_at"])

        ProblemHistory.record(
            problem=rca.problem,
            event_type=ProblemHistory.EVENT_UPDATED,
            user=user,
            comment=f"RCA {status} by {user.get_username()}.",
            new_value=comments.strip(),
            metadata={"approval_id": approval.pk},
        )

        ProblemService._notify_problem_update(
            rca.problem,
            subject=f"RCA {status} on problem #{rca.problem.pk}",
            body=comments.strip() or rca.problem.title,
            actor=user,
        )

        return approval

    # -- Notification helper ----------------------------------------

    @staticmethod
    def _notify_problem_update(problem, subject, body, actor=None):
        """
        Guarded hand-off to the notification boundary — a problem
        update must never fail because notifications did.
        """

        try:
            from apps.service_desk.services.notification_service import (
                NotificationService,
            )
        except ImportError:  # pragma: no cover - notifications optional
            return

        NotificationService.notify_problem_update(
            problem,
            subject=subject,
            body=body,
            actor=actor,
        )

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
