"""
Enterprise Service Desk
Authorization Policies

Central authorization decisions.

Phase 2.2 Authorization Hardening
"""


from django.contrib.auth.models import Group
from django.db.models import Q

from apps.service_desk.models import (
    CatalogItem,
    Change,
    CIRelationship,
    ConfigurationItem,
    Problem,
    Release,
    ServiceRequest,
    Supplier,
    Ticket,
)



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



def get_supplier_queryset(user):
    """
    Object level supplier visibility.

    Administrator:
        all suppliers

    Manager:
        suppliers tied to managed departments

    Others:
        none
    """

    if not user.is_authenticated:
        return Supplier.objects.none()

    if is_administrator(user):
        return Supplier.objects.all()

    if is_manager(user):
        return Supplier.objects.filter(
            department__in=user.managed_departments.all()
        )

    return Supplier.objects.none()



def get_catalog_item_queryset(user):
    """
    Object level catalogue-item visibility.

    Administrator / Manager:
        every item, including inactive ones — both roles administer
        the catalogue (see security/mixins.py CatalogItem*
        PermissionMixin), so they need to see retired items to
        reactivate or review them.

    Everyone else (Technician, Requester):
        active items only — an inactive item cannot be requested and
        must not appear while browsing.
    """

    if not user.is_authenticated:
        return CatalogItem.objects.none()

    if is_administrator(user) or is_manager(user):
        return CatalogItem.objects.all()

    return CatalogItem.objects.filter(is_active=True)



def get_service_request_queryset(user):
    """
    Object level service-request visibility.

    Deliberately reuses ``get_ticket_queryset`` rather than
    reimplementing role/department scoping — every ``ServiceRequest``
    wraps exactly one ``Ticket`` (ADR-011, Decision 2: "Link
    catalogue requests to existing tickets without duplicating ticket
    security"). Whatever ticket a user may see, they may see the
    matching service request, and no other.
    """

    return ServiceRequest.objects.filter(
        ticket__in=get_ticket_queryset(user)
    )



def get_change_queryset(user):
    """
    Object level change visibility.

    Administrator:
        all changes

    Manager:
        department-scoped

    Technician:
        changes they requested or are assigned to implement. Unlike
        Ticket's queue-based unassigned visibility, a Change has no
        self-assignment/claim concept (an implementer is nominated at
        approval/scheduling time) — but the Technician who *raised*
        a change must still be able to see and submit it before
        anyone has assigned an implementer, or they could never
        progress their own request past "draft".

    Requester:
        none — Change Management is an internal IT governance
        process, not requester-facing (mirrors ADR-010, Decision 1's
        Problem Management precedent; requester-facing catalogue
        requests are Service Request Management instead).
    """

    if not user.is_authenticated:
        return Change.objects.none()

    if is_administrator(user):
        return Change.objects.all()

    if is_manager(user):
        return Change.objects.filter(
            department__in=user.managed_departments.all()
        )

    if is_technician(user):
        return Change.objects.filter(
            Q(requested_by=user) | Q(assigned_to=user)
        )

    return Change.objects.none()



def get_release_queryset(user):
    """
    Object level release visibility.

    Administrator:
        all releases

    Manager:
        department-scoped

    Technician:
        releases they own

    Requester:
        none — same rationale as Change Management: internal IT
        governance, not requester-facing.
    """

    if not user.is_authenticated:
        return Release.objects.none()

    if is_administrator(user):
        return Release.objects.all()

    if is_manager(user):
        return Release.objects.filter(
            department__in=user.managed_departments.all()
        )

    if is_technician(user):
        return Release.objects.filter(owner=user)

    return Release.objects.none()



def get_configuration_item_queryset(user):
    """
    Object level CI visibility.

    Administrator:
        all CIs

    Manager:
        department-scoped, including retired/disposed items (full
        asset stewardship for departments they manage).

    Technician:
        every in-service-or-similar CI, system-wide, excluding
        retired/disposed — troubleshooting a ticket or a change
        routinely needs a CI outside the technician's own
        department, unlike Change/Release which are internal
        governance records scoped tightly by design.

    Requester:
        none — CMDB is operational/technical data, not
        requester-facing (same rationale as Change/Release).
    """

    if not user.is_authenticated:
        return ConfigurationItem.objects.none()

    if is_administrator(user):
        return ConfigurationItem.objects.all()

    if is_manager(user):
        return ConfigurationItem.objects.filter(
            department__in=user.managed_departments.all()
        )

    if is_technician(user):
        return ConfigurationItem.objects.exclude(
            status__in=[
                ConfigurationItem.STATUS_RETIRED,
                ConfigurationItem.STATUS_DISPOSED,
            ]
        )

    return ConfigurationItem.objects.none()



def get_ci_relationship_queryset(user):
    """
    A relationship is visible if its source CI is visible to the
    user — relationships are read outward from a CI you can already
    see, never used to reach a CI that would otherwise be out of
    scope.
    """

    return CIRelationship.objects.filter(
        source__in=get_configuration_item_queryset(user)
    )