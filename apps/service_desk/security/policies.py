"""
Enterprise Service Desk
Authorization Policies

Central authorization decisions.

Phase 2.2 Authorization Hardening
"""


from django.contrib.auth.models import Group
from django.db.models import Q

from apps.service_desk.models import Problem, Ticket



ROLE_ADMINISTRATOR = "Administrator"
ROLE_MANAGER = "Manager"
ROLE_TECHNICIAN = "Technician"
ROLE_REQUESTER = "Requester"



def has_role(user, role):
    """
    Check Django Group membership.
    """

    if not user.is_authenticated:
        return False

    return user.groups.filter(
        name=role
    ).exists()



def is_administrator(user):
    """
    Platform administrator access.
    """

    return (
        user.is_authenticated
        and (
            user.is_superuser
            or has_role(
                user,
                ROLE_ADMINISTRATOR
            )
        )
    )



def is_manager(user):
    """
    Department manager access.
    """

    return (
        user.is_authenticated
        and has_role(
            user,
            ROLE_MANAGER
        )
        and user.managed_departments.exists()
    )



def is_technician(user):
    """
    Technician access.
    """

    return (
        user.is_authenticated
        and has_role(
            user,
            ROLE_TECHNICIAN
        )
    )



def is_requester(user):
    """
    Default requester access.
    """

    return (
        user.is_authenticated
        and has_role(
            user,
            ROLE_REQUESTER
        )
    )



def get_ticket_queryset(user):
    """
    Object level ticket visibility.

    Rules:

    Administrator:
        all tickets

    Manager:
        department tickets

    Technician:
        assigned tickets, plus unassigned tickets (queue-based
        self-assignment — see ADR-010, Decision 2). Not scoped to
        a department/queue: no such field exists on the data model
        to scope narrower than "all unassigned tickets" without a
        new field, which was explicitly not authorized here.

    Requester:
        own tickets
    """


    if not user.is_authenticated:
        return Ticket.objects.none()


    if is_administrator(user):

        return Ticket.objects.all()


    if is_manager(user):

        return Ticket.objects.filter(
            department__in=user.managed_departments.all()
        )


    if is_technician(user):

        return Ticket.objects.filter(
            Q(assigned_to=user)
            | Q(assigned_to__isnull=True)
        )


    if is_requester(user):

        return Ticket.objects.filter(
            created_by=user
        )


    return Ticket.objects.none()



def get_problem_queryset(user):
    """
    Object level problem visibility (ADR-010, Decision 1).

    Rules:

    Administrator:
        all problems

    Manager:
        department problems

    Technician:
        assigned problems

    Requester:
        none — Requesters cannot access Problem records at all.
    """


    if not user.is_authenticated:
        return Problem.objects.none()


    if is_administrator(user):

        return Problem.objects.all()


    if is_manager(user):

        return Problem.objects.filter(
            department__in=user.managed_departments.all()
        )


    if is_technician(user):

        return Problem.objects.filter(
            assigned_to=user
        )


    return Problem.objects.none()