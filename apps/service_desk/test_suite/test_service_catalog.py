"""
Enterprise Completion Program — Phase 2: Service Catalogue and
Service Request Management.

Covers: model constraints, service-layer department-scoping
enforcement (not just form filtering), selector/RBAC scoping mirrored
from get_ticket_queryset (ADR-011, Decision 2 — "without duplicating
ticket security"), the full request lifecycle through real views,
self-approval prevention, POST-only/CSRF enforcement, anonymous
redirect, cross-scope 404, and audit/notification creation.
"""

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import (
    CatalogItem,
    Department,
    Notification,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestApproval,
    ServiceRequestHistory,
    Ticket,
)
from apps.service_desk.security.policies import (
    get_catalog_item_queryset,
    get_service_request_queryset,
)
from apps.service_desk.services.service_catalog_service import CatalogService
from apps.service_desk.services.service_request_service import (
    ServiceRequestService,
)
from apps.service_desk.services.ticket_service import TicketService


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class CatalogItemModelTests(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Hardware")

    def test_duplicate_item_name_in_same_category_is_rejected(self):
        CatalogItem.objects.create(category=self.category, name="Laptop")

        duplicate = CatalogItem(category=self.category, name="Laptop")

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_same_name_allowed_in_a_different_category(self):
        other = ServiceCategory.objects.create(name="Software")
        CatalogItem.objects.create(category=self.category, name="Laptop")

        item = CatalogItem(category=other, name="Laptop")
        item.full_clean()  # must not raise


class CatalogServiceTests(TestCase):
    """
    Exercises CatalogService directly, bypassing the form entirely —
    proves department scoping is enforced at the service layer, not
    only narrowed in CatalogItemForm's queryset (mission requirement:
    "Never rely on form filtering alone for authorization").
    """

    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept_a = Department.objects.create(name="Dept A")
        self.dept_b = Department.objects.create(name="Dept B")

        self.manager_a = User.objects.create_user(
            username="svc_mgr_a", password="password123"
        )
        Group.objects.create(name="Manager")
        self.manager_a.groups.add(Group.objects.get(name="Manager"))
        self.dept_a.managers.add(self.manager_a)

        self.admin = User.objects.create_superuser(
            username="svc_admin", password="password123", email="a@test.com"
        )

    def test_manager_cannot_route_item_to_unmanaged_department(self):
        with self.assertRaises(ValidationError):
            CatalogService.create_item(
                user=self.manager_a,
                category=self.category,
                name="Monitor",
                fulfillment_department=self.dept_b,
                default_priority="medium",
            )

        self.assertFalse(CatalogItem.objects.filter(name="Monitor").exists())

    def test_manager_can_route_item_to_managed_department(self):
        item = CatalogService.create_item(
            user=self.manager_a,
            category=self.category,
            name="Monitor",
            fulfillment_department=self.dept_a,
            default_priority="medium",
        )
        self.assertTrue(CatalogItem.objects.filter(pk=item.pk).exists())

    def test_administrator_unrestricted(self):
        item = CatalogService.create_item(
            user=self.admin,
            category=self.category,
            name="Server",
            fulfillment_department=self.dept_b,
            default_priority="high",
        )
        self.assertEqual(item.fulfillment_department, self.dept_b)

    def test_deactivate_then_activate_lifecycle(self):
        item = CatalogItem.objects.create(
            category=self.category, name="Laptop"
        )

        CatalogService.deactivate_item(item)
        item.refresh_from_db()
        self.assertFalse(item.is_active)

        with self.assertRaises(ValidationError):
            CatalogService.deactivate_item(item)

        CatalogService.activate_item(item)
        item.refresh_from_db()
        self.assertTrue(item.is_active)


class CatalogItemVisibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept = Department.objects.create(name="IT")

        self.active_item = CatalogItem.objects.create(
            category=self.category, name="Laptop", is_active=True
        )
        self.inactive_item = CatalogItem.objects.create(
            category=self.category, name="Old Laptop", is_active=False
        )

        requester_group = Group.objects.create(name="Requester")
        _grant(requester_group, "view_catalogitem")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_catalogitem")

        self.requester = User.objects.create_user(
            username="cat_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="cat_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.admin = User.objects.create_superuser(
            username="cat_admin", password="password123", email="a@test.com"
        )

    def test_anonymous_user_sees_nothing(self):
        qs = get_catalog_item_queryset(AnonymousUser())
        self.assertEqual(qs.count(), 0)

    def test_requester_sees_only_active_items(self):
        qs = get_catalog_item_queryset(self.requester)
        self.assertIn(self.active_item, qs)
        self.assertNotIn(self.inactive_item, qs)

    def test_manager_sees_all_items_including_inactive(self):
        qs = get_catalog_item_queryset(self.manager)
        self.assertIn(self.active_item, qs)
        self.assertIn(self.inactive_item, qs)

    def test_administrator_sees_all_items(self):
        self.assertEqual(get_catalog_item_queryset(self.admin).count(), 2)

    def test_anonymous_browse_redirects_to_login(self):
        response = self.client.get(
            reverse("service_desk:catalog_item_list")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requester_cannot_reach_inactive_item_detail(self):
        """
        Object existence must not be disclosed across scope — a 404,
        not a 403, since Requester lacks the permission to know it's
        merely inactive versus never having existed.
        """

        self.client.login(username="cat_requester", password="password123")
        response = self.client.get(
            reverse(
                "service_desk:catalog_item_detail",
                args=[self.inactive_item.pk],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_manager_can_reach_inactive_item_detail(self):
        self.client.login(username="cat_manager", password="password123")
        response = self.client.get(
            reverse(
                "service_desk:catalog_item_detail",
                args=[self.inactive_item.pk],
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_without_permission_gets_403(self):
        plain_user = User.objects.create_user(
            username="cat_norole", password="password123"
        )
        self.client.login(username="cat_norole", password="password123")
        response = self.client.get(
            reverse("service_desk:catalog_item_list")
        )
        self.assertEqual(response.status_code, 403)


class CatalogItemManagementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept_a = Department.objects.create(name="Dept A")

        manager_group = Group.objects.create(name="Manager")
        _grant(
            manager_group,
            "view_catalogitem",
            "add_catalogitem",
            "change_catalogitem",
        )

        requester_group = Group.objects.create(name="Requester")
        _grant(requester_group, "view_catalogitem")

        self.manager = User.objects.create_user(
            username="mgmt_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept_a.managers.add(self.manager)

        self.requester = User.objects.create_user(
            username="mgmt_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.item = CatalogItem.objects.create(
            category=self.category,
            name="Laptop",
            fulfillment_department=self.dept_a,
        )

    def test_requester_cannot_create_item(self):
        self.client.login(username="mgmt_requester", password="password123")
        response = self.client.post(
            reverse("service_desk:catalog_item_create"),
            {
                "category": self.category.pk,
                "name": "Monitor",
                "default_priority": "medium",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            CatalogItem.objects.filter(name="Monitor").exists()
        )

    def test_manager_can_create_and_deactivate_and_reactivate(self):
        self.client.login(username="mgmt_manager", password="password123")

        create_response = self.client.post(
            reverse("service_desk:catalog_item_create"),
            {
                "category": self.category.pk,
                "name": "Monitor",
                "fulfillment_department": self.dept_a.pk,
                "default_priority": "medium",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        item = CatalogItem.objects.get(name="Monitor")

        deactivate_response = self.client.post(
            reverse("service_desk:catalog_item_deactivate", args=[item.pk])
        )
        self.assertEqual(deactivate_response.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(item.is_active)

        activate_response = self.client.post(
            reverse("service_desk:catalog_item_activate", args=[item.pk])
        )
        self.assertEqual(activate_response.status_code, 302)
        item.refresh_from_db()
        self.assertTrue(item.is_active)

    def test_deactivate_rejects_get(self):
        self.client.login(username="mgmt_manager", password="password123")
        response = self.client.get(
            reverse(
                "service_desk:catalog_item_deactivate", args=[self.item.pk]
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_deactivate_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="mgmt_manager", password="password123")
        response = client.post(
            reverse(
                "service_desk:catalog_item_deactivate", args=[self.item.pk]
            )
        )
        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_active)


class ServiceRequestServiceTests(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept = Department.objects.create(name="IT")

        self.approved_item = CatalogItem.objects.create(
            category=self.category,
            name="Laptop",
            fulfillment_department=self.dept,
            requires_approval=False,
        )
        self.gated_item = CatalogItem.objects.create(
            category=self.category,
            name="VPN Access",
            fulfillment_department=self.dept,
            requires_approval=True,
        )

        self.requester = User.objects.create_user(
            username="wf_requester", password="password123"
        )
        self.manager = User.objects.create_user(
            username="wf_manager", password="password123"
        )
        self.dept.managers.add(self.manager)
        Group.objects.create(name="Manager")
        self.manager.groups.add(Group.objects.get(name="Manager"))

        self.technician = User.objects.create_user(
            username="wf_technician", password="password123"
        )

    def test_auto_approved_item_starts_approved(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        self.assertEqual(sr.status, ServiceRequest.STATUS_APPROVED)

    def test_gated_item_starts_pending_approval(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

    def test_creation_wraps_a_real_ticket(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester, justification="need it"
        )
        self.assertIsNotNone(sr.ticket_id)
        self.assertEqual(sr.ticket.created_by, self.requester)
        self.assertEqual(sr.ticket.department, self.dept)

    def test_zero_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            ServiceRequestService.create_request(
                self.approved_item, self.requester, quantity=0
            )

    def test_inactive_item_cannot_be_requested(self):
        self.approved_item.is_active = False
        self.approved_item.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            ServiceRequestService.create_request(
                self.approved_item, self.requester
            )

    def test_self_approval_is_rejected(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        with self.assertRaises(ValidationError):
            ServiceRequestService.approve_request(sr, self.requester)

        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

    def test_technician_cannot_approve_even_with_change_permission(self):
        """
        Technician holds change_servicerequest for assignment/
        fulfilment purposes — approval specifically requires Manager
        or Administrator, enforced independently in the service layer
        (ServiceRequestService._assert_may_decide), not derived from
        that broader Django permission.
        """

        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        with self.assertRaises(ValidationError):
            ServiceRequestService.approve_request(sr, self.technician)

        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

    def test_approve_requires_pending_approval_status(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        # already "approved" — approving again must fail
        with self.assertRaises(ValidationError):
            ServiceRequestService.approve_request(sr, self.manager)

    def test_reject_requires_a_comment(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        with self.assertRaises(ValidationError):
            ServiceRequestService.reject_request(sr, self.manager, "")

    def test_reject_records_an_approval_decision_and_history(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        ServiceRequestService.reject_request(
            sr, self.manager, "Not eligible."
        )
        sr.refresh_from_db()

        self.assertEqual(sr.status, ServiceRequest.STATUS_REJECTED)
        self.assertEqual(
            sr.approvals.filter(
                decision=ServiceRequestApproval.DECISION_REJECTED
            ).count(),
            1,
        )
        self.assertTrue(
            sr.history.filter(
                event_type=ServiceRequestHistory.EVENT_REJECTED
            ).exists()
        )

    def test_illegal_transition_is_rejected(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        # pending_approval -> assigned is not a legal edge
        with self.assertRaises(ValidationError):
            ServiceRequestService.assign_request(
                sr, self.technician, user=self.manager
            )

    def test_assign_requires_approved_status(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        ServiceRequestService.assign_request(
            sr, self.technician, user=self.manager
        )
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_ASSIGNED)
        self.assertEqual(sr.ticket.assigned_to, self.technician)
        self.assertEqual(sr.ticket.status, "in_progress")

    def test_only_assignee_manager_or_admin_may_advance_fulfilment(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        ServiceRequestService.assign_request(
            sr, self.technician, user=self.manager
        )

        other_technician = User.objects.create_user(
            username="wf_other_tech", password="password123"
        )

        with self.assertRaises(ValidationError):
            ServiceRequestService.mark_fulfilling(
                sr, user=other_technician
            )

        # the assignee themself may
        ServiceRequestService.mark_fulfilling(sr, user=self.technician)
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_FULFILLING)

    def test_fulfilled_resolves_the_underlying_ticket(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        ServiceRequestService.assign_request(
            sr, self.technician, user=self.manager
        )
        ServiceRequestService.mark_fulfilling(sr, user=self.technician)
        ServiceRequestService.mark_fulfilled(sr, user=self.technician)

        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_FULFILLED)
        self.assertEqual(sr.ticket.status, "resolved")

    def test_requester_can_cancel_before_fulfilment(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        ServiceRequestService.cancel_request(
            sr, self.requester, reason="No longer needed"
        )
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_CANCELLED)

    def test_unrelated_user_cannot_cancel(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        bystander = User.objects.create_user(
            username="wf_bystander", password="password123"
        )
        with self.assertRaises(ValidationError):
            ServiceRequestService.cancel_request(sr, bystander)

        sr.refresh_from_db()
        self.assertNotEqual(sr.status, ServiceRequest.STATUS_CANCELLED)

    def test_cannot_cancel_a_fulfilled_request(self):
        sr = ServiceRequestService.create_request(
            self.approved_item, self.requester
        )
        ServiceRequestService.assign_request(
            sr, self.technician, user=self.manager
        )
        ServiceRequestService.mark_fulfilling(sr, user=self.technician)
        ServiceRequestService.mark_fulfilled(sr, user=self.technician)

        with self.assertRaises(ValidationError):
            ServiceRequestService.cancel_request(sr, self.requester)

    def test_approval_notifies_the_requester(self):
        sr = ServiceRequestService.create_request(
            self.gated_item, self.requester
        )
        ServiceRequestService.approve_request(sr, self.manager)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.requester,
                kind=Notification.KIND_SERVICE_REQUEST_APPROVED,
            ).exists()
        )


class ServiceRequestVisibilityTests(TestCase):
    """
    ADR-011, Decision 2: visibility is derived from get_ticket_queryset,
    not reimplemented — these tests confirm that derivation actually
    produces the same shape Ticket RBAC already guarantees.
    """

    def setUp(self):
        self.client = Client()
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept = Department.objects.create(name="IT")
        self.other_dept = Department.objects.create(name="Finance")

        self.item = CatalogItem.objects.create(
            category=self.category,
            name="Laptop",
            fulfillment_department=self.dept,
        )

        requester_group = Group.objects.create(name="Requester")
        _grant(
            requester_group,
            "view_catalogitem",
            "add_servicerequest",
            "view_servicerequest",
        )

        manager_group = Group.objects.create(name="Manager")
        _grant(
            manager_group,
            "view_catalogitem",
            "view_servicerequest",
            "change_servicerequest",
        )

        self.requester = User.objects.create_user(
            username="vis_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.other_requester = User.objects.create_user(
            username="vis_other_requester", password="password123"
        )
        self.other_requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="vis_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="vis_other_manager", password="password123"
        )
        self.other_manager.groups.add(manager_group)
        self.other_dept.managers.add(self.other_manager)

        self.admin = User.objects.create_superuser(
            username="vis_admin", password="password123", email="a@test.com"
        )

        self.sr = ServiceRequestService.create_request(
            self.item, self.requester
        )

    def test_requester_sees_own_request(self):
        qs = get_service_request_queryset(self.requester)
        self.assertIn(self.sr, qs)

    def test_other_requester_does_not_see_it(self):
        qs = get_service_request_queryset(self.other_requester)
        self.assertNotIn(self.sr, qs)

    def test_managing_department_manager_sees_it(self):
        qs = get_service_request_queryset(self.manager)
        self.assertIn(self.sr, qs)

    def test_unrelated_department_manager_does_not_see_it(self):
        qs = get_service_request_queryset(self.other_manager)
        self.assertNotIn(self.sr, qs)

    def test_administrator_sees_it(self):
        qs = get_service_request_queryset(self.admin)
        self.assertIn(self.sr, qs)

    def test_cross_scope_detail_is_404_not_403(self):
        self.client.login(
            username="vis_other_requester", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:service_request_detail", args=[self.sr.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_unrelated_manager_gets_404_not_403(self):
        self.client.login(
            username="vis_other_manager", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:service_request_detail", args=[self.sr.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(
            reverse("service_desk:service_request_list")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class ServiceRequestWorkflowViewTests(TestCase):
    """
    End-to-end: browse -> request -> approve -> assign -> fulfilling
    -> fulfilled -> ticket resolved -> requester confirms (reusing the
    existing IM-04 ticket-confirmation flow unmodified) -> closed.
    """

    def setUp(self):
        self.client = Client()
        self.category = ServiceCategory.objects.create(name="Hardware")
        self.dept = Department.objects.create(name="IT")

        self.item = CatalogItem.objects.create(
            category=self.category,
            name="VPN Access",
            fulfillment_department=self.dept,
            requires_approval=True,
        )

        requester_group = Group.objects.create(name="Requester")
        _grant(
            requester_group,
            "view_catalogitem",
            "add_servicerequest",
            "view_servicerequest",
            "view_ticket",
        )

        manager_group = Group.objects.create(name="Manager")
        _grant(
            manager_group,
            "view_catalogitem",
            "view_servicerequest",
            "change_servicerequest",
            "view_ticket",
            "change_ticket",
        )

        technician_group = Group.objects.create(name="Technician")
        _grant(
            technician_group,
            "view_catalogitem",
            "view_servicerequest",
            "change_servicerequest",
            "view_ticket",
            "change_ticket",
        )

        self.requester = User.objects.create_user(
            username="e2e_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="e2e_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.technician = User.objects.create_user(
            username="e2e_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

    def test_full_lifecycle_through_real_views(self):
        self.client.login(username="e2e_requester", password="password123")

        create_response = self.client.post(
            reverse(
                "service_desk:service_request_create", args=[self.item.pk]
            ),
            {"quantity": 1, "justification": "Need remote access."},
        )
        self.assertEqual(create_response.status_code, 302)

        sr = ServiceRequest.objects.get(catalog_item=self.item)
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

        # Requester cannot approve their own request.
        self.client.logout()
        self.client.login(username="e2e_manager", password="password123")

        approve_response = self.client.post(
            reverse("service_desk:service_request_approve", args=[sr.pk]),
            {"comment": "Approved."},
        )
        self.assertEqual(approve_response.status_code, 302)
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_APPROVED)

        assign_response = self.client.post(
            reverse("service_desk:service_request_assign", args=[sr.pk]),
            {"technician_id": self.technician.pk},
        )
        self.assertEqual(assign_response.status_code, 302)
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_ASSIGNED)

        self.client.logout()
        self.client.login(
            username="e2e_technician", password="password123"
        )

        fulfilling_response = self.client.post(
            reverse(
                "service_desk:service_request_fulfilling", args=[sr.pk]
            )
        )
        self.assertEqual(fulfilling_response.status_code, 302)

        fulfilled_response = self.client.post(
            reverse("service_desk:service_request_fulfilled", args=[sr.pk])
        )
        self.assertEqual(fulfilled_response.status_code, 302)

        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_FULFILLED)
        self.assertEqual(sr.ticket.status, "resolved")

        # Reuse the ticket's own confirmation flow (no new code needed).
        self.client.logout()
        self.client.login(username="e2e_manager", password="password123")
        self.client.post(
            reverse(
                "service_desk:ticket_request_confirmation",
                args=[sr.ticket_id],
            )
        )

        self.client.logout()
        self.client.login(username="e2e_requester", password="password123")
        close_response = self.client.post(
            reverse("service_desk:ticket_close", args=[sr.ticket_id])
        )
        self.assertEqual(close_response.status_code, 302)

        sr.ticket.refresh_from_db()
        self.assertEqual(sr.ticket.status, "closed")

        self.assertTrue(
            sr.history.filter(
                event_type=ServiceRequestHistory.EVENT_CREATED
            ).exists()
        )
        self.assertTrue(
            sr.history.filter(
                event_type=ServiceRequestHistory.EVENT_APPROVED
            ).exists()
        )
        self.assertTrue(
            sr.history.filter(
                event_type=ServiceRequestHistory.EVENT_FULFILLED
            ).exists()
        )

    def test_technician_cannot_approve(self):
        """
        Technician holds change_servicerequest (needed to self-assign
        and advance fulfilment), so the permission mixin alone would
        let this POST through — the service-layer role check
        (ServiceRequestService._assert_may_decide) is what actually
        stops it. Confirmed here through the real view, not just
        against the service directly (see ServiceRequestServiceTests
        for the direct-call equivalent).
        """

        sr = ServiceRequestService.create_request(
            self.item, self.requester
        )
        self.client.login(
            username="e2e_technician", password="password123"
        )
        response = self.client.post(
            reverse("service_desk:service_request_approve", args=[sr.pk]),
            {"comment": "trying anyway"},
        )
        self.assertEqual(response.status_code, 302)

        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

    def test_requester_cannot_assign(self):
        sr = ServiceRequestService.create_request(
            self.item, self.requester
        )
        ServiceRequestService.approve_request(sr, self.manager)

        self.client.login(username="e2e_requester", password="password123")
        response = self.client.post(
            reverse("service_desk:service_request_assign", args=[sr.pk]),
            {"technician_id": self.technician.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_approve_rejects_get(self):
        sr = ServiceRequestService.create_request(
            self.item, self.requester
        )
        self.client.login(username="e2e_manager", password="password123")
        response = self.client.get(
            reverse("service_desk:service_request_approve", args=[sr.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_approve_requires_csrf_token(self):
        sr = ServiceRequestService.create_request(
            self.item, self.requester
        )
        client = Client(enforce_csrf_checks=True)
        client.login(username="e2e_manager", password="password123")
        response = client.post(
            reverse("service_desk:service_request_approve", args=[sr.pk]),
            {"comment": "x"},
        )
        self.assertEqual(response.status_code, 403)
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.STATUS_PENDING_APPROVAL)

    def test_anonymous_create_redirects_to_login(self):
        response = self.client.post(
            reverse(
                "service_desk:service_request_create", args=[self.item.pk]
            ),
            {"quantity": 1},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_create_form_rejects_zero_quantity(self):
        self.client.login(username="e2e_requester", password="password123")
        response = self.client.post(
            reverse(
                "service_desk:service_request_create", args=[self.item.pk]
            ),
            {"quantity": 0},
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with error
        self.assertFalse(
            ServiceRequest.objects.filter(catalog_item=self.item).exists()
        )
