"""
Enterprise Service Desk
Authorization Policies

Central authorization decisions.
"""


from apps.service_desk.models import Ticket



def is_administrator(user):
    """
    Platform administrators bypass object restrictions.
    """

    return (
        user.is_authenticated
        and user.is_superuser
    )



def is_manager(user):
    """
    User manages one or more departments.
    """

    return (
        user.is_authenticated
        and user.managed_departments.exists()
    )



def is_technician(user):
    """
    User has assigned tickets.
    """

    return (
        user.is_authenticated
        and user.assigned_tickets.exists()
    )



def get_ticket_queryset(user):
    """
    Returns tickets visible to the user.

    Rules:

    Administrator:
        all tickets

    Manager:
        department tickets

    Technician:
        assigned tickets

    Requester:
        created tickets
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


    return Ticket.objects.filter(
        created_by=user
    )