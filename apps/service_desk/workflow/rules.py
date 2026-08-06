"""
Enterprise Service Desk
Workflow Rules Engine

Responsibilities
---------------
- Defines valid ticket lifecycle transitions.
- Centralizes workflow validation.
- Prevents invalid state changes.
"""

from dataclasses import dataclass

from apps.service_desk.models import Ticket


@dataclass(frozen=True)
class WorkflowResult:
    success: bool
    message: str


WORKFLOW = {
    "open": {
        "in_progress",
        "pending",
        "closed",
    },
    "in_progress": {
        "pending",
        "resolved",
        "closed",
    },
    "pending": {
        "in_progress",
        "resolved",
        "closed",
    },
    "resolved": {
        "closed",
        "in_progress",
    },
    "closed": set(),
}


def allowed_statuses(status: str) -> set[str]:
    """
    Return all valid transitions
    for a given status.
    """
    return WORKFLOW.get(status, set())


def can_transition(
    current_status: str,
    new_status: str,
) -> bool:
    """
    True if transition is permitted.
    """

    return new_status in allowed_statuses(current_status)


def validate_transition(
    ticket: Ticket,
    new_status: str,
) -> WorkflowResult:
    """
    Validate a workflow transition.
    """

    if ticket.status == new_status:

        return WorkflowResult(
            False,
            "Ticket is already in that status.",
        )

    if not can_transition(
        ticket.status,
        new_status,
    ):

        return WorkflowResult(
            False,
            f"Invalid transition "
            f"{ticket.status} → {new_status}",
        )

    return WorkflowResult(
        True,
        "Transition allowed.",
    )