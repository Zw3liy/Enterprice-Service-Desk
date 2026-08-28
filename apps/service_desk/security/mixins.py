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


class SupplierChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Supplier update / lifecycle permission.
    """

    permission_required = (
        "service_desk.change_supplier",
    )


# =====================================================
# SLA Permissions
# =====================================================


class SLAPolicyViewPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    SLA policy viewing permission.
    """

    permission_required = (
        "service_desk.view_slapolicy"
    )


class SLAPolicyChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    SLA policy creation/update permission.
    """

    permission_required = (
        "service_desk.change_slapolicy"
    )


# =====================================================
# Catalogue Item Permissions
# =====================================================


class CatalogItemPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base catalogue-item access permission.

    Default permission:
        view_catalogitem
    """

    permission_required = (
        "service_desk.view_catalogitem"
    )


class CatalogItemViewPermissionMixin(
    CatalogItemPermissionMixin
):
    """
    Catalogue browsing permission.
    """

    permission_required = (
        "service_desk.view_catalogitem"
    )


class CatalogItemCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Catalogue-item creation permission.
    """

    permission_required = (
        "service_desk.add_catalogitem"
    )


class CatalogItemChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Catalogue-item update / lifecycle permission.
    """

    permission_required = (
        "service_desk.change_catalogitem"
    )


# =====================================================
# Service Request Permissions
# =====================================================


class ServiceRequestPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base service-request access permission.

    Default permission:
        view_servicerequest
    """

    permission_required = (
        "service_desk.view_servicerequest"
    )


class ServiceRequestViewPermissionMixin(
    ServiceRequestPermissionMixin
):
    """
    Service-request viewing permission.
    """

    permission_required = (
        "service_desk.view_servicerequest"
    )


class ServiceRequestCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Service-request creation permission.
    """

    permission_required = (
        "service_desk.add_servicerequest"
    )


class ServiceRequestChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Service-request workflow-transition permission.

    Covers approve/reject/assign/fulfilling/fulfilled/cancel — every
    transition additionally re-checks the specific actor rule it
    needs (e.g. self-approval prevention) at the service layer, this
    mixin only gates "staff of some kind, not an anonymous or
    unrelated Requester".
    """

    permission_required = (
        "service_desk.change_servicerequest"
    )


# =====================================================
# Change Permissions
# =====================================================


class ChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base change access permission.

    Default permission:
        view_change
    """

    permission_required = (
        "service_desk.view_change"
    )


class ChangeViewPermissionMixin(
    ChangePermissionMixin
):
    """
    Change viewing permission.
    """

    permission_required = (
        "service_desk.view_change"
    )


class ChangeCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Change creation permission.
    """

    permission_required = (
        "service_desk.add_change"
    )


class ChangeChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Change workflow-transition permission.

    Covers submit/assess/approve/reject/schedule/implement/validate/
    complete/fail/rollback — every transition additionally re-checks
    the specific actor rule it needs (e.g. approval separation of
    duties) at the service layer; this mixin only gates "staff of
    some kind".
    """

    permission_required = (
        "service_desk.change_change"
    )


# =====================================================
# Release Permissions
# =====================================================


class ReleasePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base release access permission.

    Default permission:
        view_release
    """

    permission_required = (
        "service_desk.view_release"
    )


class ReleaseViewPermissionMixin(
    ReleasePermissionMixin
):
    """
    Release viewing permission.
    """

    permission_required = (
        "service_desk.view_release"
    )


class ReleaseCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Release creation permission.
    """

    permission_required = (
        "service_desk.add_release"
    )


class ReleaseChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Release workflow-transition permission.

    Covers approve/schedule/link-change/unlink-change/assign-owner/
    deploy/validate/complete/fail/rollback — every transition
    additionally re-checks the specific actor rule it needs at the
    service layer; this mixin only gates "staff of some kind".
    """

    permission_required = (
        "service_desk.change_release"
    )


# =====================================================
# CMDB Permissions
# =====================================================


class ConfigurationItemPermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base CI access permission.

    Default permission:
        view_configurationitem
    """

    permission_required = (
        "service_desk.view_configurationitem"
    )


class ConfigurationItemViewPermissionMixin(
    ConfigurationItemPermissionMixin
):
    """
    CI viewing permission.
    """

    permission_required = (
        "service_desk.view_configurationitem"
    )


class ConfigurationItemCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    CI creation permission.
    """

    permission_required = (
        "service_desk.add_configurationitem"
    )


class ConfigurationItemChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    CI update / relationship / linking permission.
    """

    permission_required = (
        "service_desk.change_configurationitem"
    )


# =====================================================
# Knowledge Permissions
# =====================================================


class KnowledgeArticlePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Base knowledge-article access permission.

    Default permission:
        view_knowledgearticle
    """

    permission_required = (
        "service_desk.view_knowledgearticle"
    )


class KnowledgeArticleViewPermissionMixin(
    KnowledgeArticlePermissionMixin
):
    """
    Knowledge-article viewing permission.
    """

    permission_required = (
        "service_desk.view_knowledgearticle"
    )


class KnowledgeArticleCreatePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Knowledge-article creation permission.
    """

    permission_required = (
        "service_desk.add_knowledgearticle"
    )


class KnowledgeArticleChangePermissionMixin(
    ServiceDeskPermissionMixin
):
    """
    Knowledge-article workflow-transition permission.

    Covers submit/assign-reviewer/approve/send-back/publish/archive/
    revise — every transition additionally re-checks the specific
    actor rule it needs (e.g. reviewer separation of duties) at the
    service layer; this mixin only gates "staff of some kind".
    """

    permission_required = (
        "service_desk.change_knowledgearticle"
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