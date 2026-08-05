"""
apps/service_desk/security/mixins.py

Enterprise Service Desk
Authorization Enforcement Layer

Permanent security enforcement layer.

Responsibilities:
- Authentication enforcement
- Permission enforcement
- Role enforcement
- Object authorization hooks

Design:
Views declare security requirements.
Mixins enforce them.
Policies decide object visibility.

Do not place authorization logic in views.
"""

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)

from django.core.exceptions import PermissionDenied


# =====================================================
# Base Security Mixins
# =====================================================


class ServiceDeskLoginRequiredMixin(
    LoginRequiredMixin
):
    """
    Base authentication enforcement.

    All protected service desk views
    should inherit this.
    """

    login_url = "/accounts/login/"



class ServiceDeskPermissionMixin(
    ServiceDeskLoginRequiredMixin,
    PermissionRequiredMixin,
):
    """
    Base permission enforcement.

    Uses Django permissions.

    Missing permissions:
        HTTP 403
    """

    raise_exception = True



# =====================================================
# Ticket Permissions
# =====================================================


class TicketPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base ticket access permission.

    Kept permanently for compatibility.

    Default permission:
        view_ticket
    """

    permission_required = (
        "service_desk.view_ticket"
    )



class TicketViewPermissionMixin(
    TicketPermissionMixin
):
    """
    Ticket viewing permission.
    """

    permission_required = (
        "service_desk.view_ticket"
    )



class TicketCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Ticket creation permission.
    """

    permission_required = (
        "service_desk.add_ticket"
    )



class TicketChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Ticket update permission.
    """

    permission_required = (
        "service_desk.change_ticket"
    )



class TicketDeletePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Ticket deletion permission.
    """

    permission_required = (
        "service_desk.delete_ticket"
    )



# =====================================================
# Role Enforcement
# =====================================================


class RoleRequiredMixin(
    ServiceDeskLoginRequiredMixin
):
    """
    Generic Django Group enforcement.

    Example:

    required_role = "Manager"
    """

    required_role = None


    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        if (
            self.required_role
            and not request.user.groups.filter(
                name=self.required_role
            ).exists()
            and not request.user.is_superuser
        ):
            raise PermissionDenied

        return super().dispatch(
            request,
            *args,
            **kwargs
        )



# =====================================================
# Administrator Enforcement
# =====================================================


class AdministratorRequiredMixin(
    ServiceDeskLoginRequiredMixin
):
    """
    Administrator-only access.

    Uses Django superuser flag.
    """

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        if not request.user.is_superuser:
            raise PermissionDenied

        return super().dispatch(
            request,
            *args,
            **kwargs
        )