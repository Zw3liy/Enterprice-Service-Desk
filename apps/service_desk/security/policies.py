"""
Enterprise Service Desk
Authorization Policies

Central authorization decisions.

Phase 2.2 Authorization Hardening
"""


from django.contrib.auth.models import Group

from apps.service_desk.models import Ticket



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
        assigned tickets

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
            assigned_to=user
        )


    if is_requester(user):

        return Ticket.objects.filter(
            created_by=user
        )


    return Ticket.objects.none()