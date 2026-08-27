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
from django.contrib.auth.views import redirect_to_login

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

    Anonymous request:
        redirect to the login page (there is nothing to deny yet —
        the user has simply not identified themselves)

    Authenticated request missing the permission:
        HTTP 403
    """

    raise_exception = True

    def handle_no_permission(self):
        """
        Split the anonymous and authenticated failure paths.

        ``raise_exception = True`` alone makes *every* failure a 403,
        including for logged-out visitors, which hides the login page
        behind an error and leaks no route to authenticate. Anonymous
        users are redirected to ``login_url`` instead; authenticated
        users still get a hard 403.
        """

        user = getattr(self.request, "user", None)

        if user is None or not user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )

        return super().handle_no_permission()



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
# Problem Permissions
# =====================================================


class ProblemPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base problem access permission.

    Default permission:
        view_problem
    """

    permission_required = (
        "service_desk.view_problem"
    )



class ProblemViewPermissionMixin(
    ProblemPermissionMixin
):
    """
    Problem viewing permission.
    """

    permission_required = (
        "service_desk.view_problem"
    )



class ProblemCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Problem creation permission.
    """

    permission_required = (
        "service_desk.add_problem"
    )



class ProblemChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Problem update permission.
    """

    permission_required = (
        "service_desk.change_problem"
    )



class ProblemDeletePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Problem deletion permission.
    """

    permission_required = (
        "service_desk.delete_problem"
    )


# =====================================================
# Supplier Permissions


class SupplierPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base supplier access permission.
    """

    permission_required = (
        "service_desk.view_supplier",
    )


class SupplierViewPermissionMixin(
    SupplierPermissionMixin
):
    """
    Supplier viewing permission.
    """

    permission_required = (
        "service_desk.view_supplier",
    )


class SupplierCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Supplier creation permission.
    """

    permission_required = (
        "service_desk.add_supplier",
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

        # Anonymous visitors must reach the login redirect handled by
        # LoginRequiredMixin, not a 403 — checking the role first would
        # deny them before they ever get the chance to authenticate.
        if not request.user.is_authenticated:
            return super().dispatch(
                request,
                *args,
                **kwargs
            )

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

        if not request.user.is_authenticated:
            return super().dispatch(
                request,
                *args,
                **kwargs
            )

        if not request.user.is_superuser:
            raise PermissionDenied

        return super().dispatch(
            request,
            *args,
            **kwargs
        )