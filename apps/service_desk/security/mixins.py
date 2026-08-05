"""
apps/service_desk/security/mixins.py

Enterprise Service Desk
Authorization Hardening Layer

Provides reusable authorization mixins
for class-based views.

Phase 2.2.4
"""


from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)


class TicketPermissionMixin(
    LoginRequiredMixin,
    PermissionRequiredMixin,
):
    """
    Base authorization mixin for Ticket views.

    Enforcement order:

    1. User must authenticate
    2. User must have Django permission
    3. View continues to object-level policy checks

    Used by:
        TicketListView
        TicketCreateView
        TicketDetailView
    """

    raise_exception = True

    login_url = "/accounts/login/"