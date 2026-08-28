"""
Enterprise Completion Program — Phase 5: CMDB.

Covers: model-level and service-level rejection of self-relationships
and duplicate relationships, service-layer department-scoping
enforcement independent of form filtering, RBAC scoping (Requester
excluded entirely; Technician sees active items system-wide but not
retired/disposed; Manager department-scoped including retired items),
linking to tickets/changes through each side's own RBAC-scoped
queryset, cross-scope 404, anonymous redirect, POST-only/CSRF, and
the full lifecycle through real views.
"""

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import (
    CIRelationship,
    Change,
    ConfigurationItem,
    ConfigurationItemType,
    Department,
    Ticket,
)
from apps.service_desk.security.policies import (
    get_ci_relationship_queryset,
    get_configuration_item_queryset,
)
from apps.service_desk.services.change_service import ChangeService
from apps.service_desk.services.cmdb_service import CMDBService


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class ConfigurationItemModelTests(TestCase):
    def setUp(self):
        self.ci_type = ConfigurationItemType.objects.create(name="Server")
        self.a = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-01", identifier="SRV-001"
        )
        self.b = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="db-01", identifier="SRV-002"
        )

    def test_duplicate_identifier_is_rejected(self):
        duplicate = ConfigurationItem(
            ci_type=self.ci_type, name="app-02", identifier="SRV-001"
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_self_relationship_rejected_at_model_level(self):
        relationship = CIRelationship(
            source=self.a,
            target=self.a,
            relationship_type=CIRelationship.TYPE_DEPENDS_ON,
        )
        with self.assertRaises(ValidationError):
            relationship.clean()

    def test_valid_relationship_is_created(self):
        relationship = CIRelationship.objects.create(
            source=self.a,
            target=self.b,
            relationship_type=CIRelationship.TYPE_DEPENDS_ON,
        )
        self.assertEqual(relationship.source, self.a)
        self.assertEqual(relationship.target, self.b)


class CMDBServiceTests(TestCase):
    def setUp(self):
        self.ci_type = ConfigurationItemType.objects.create(name="Server")
        self.dept_a = Department.objects.create(name="Dept A")
        self.dept_b = Department.objects.create(name="Dept B")

        self.manager_a = User.objects.create_user(
            username="cmdb_mgr_a", password="password123"
        )
        Group.objects.create(name="Manager")
        self.manager_a.groups.add(Group.objects.get(name="Manager"))
        self.dept_a.managers.add(self.manager_a)

        self.admin = User.objects.create_superuser(
            username="cmdb_admin", password="password123", email="a@test.com"
        )

        self.a = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-01", identifier="SRV-001",
            department=self.dept_a,
        )
        self.b = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="db-01", identifier="SRV-002",
            department=self.dept_a,
        )

    def test_manager_cannot_create_ci_for_unmanaged_department(self):
        with self.assertRaises(ValidationError):
            CMDBService.create_ci(
                user=self.manager_a,
                ci_type=self.ci_type,
                name="switch-01",
                identifier="SRV-003",
                department=self.dept_b,
            )
        self.assertFalse(
            ConfigurationItem.objects.filter(identifier="SRV-003").exists()
        )

    def test_manager_can_create_ci_for_managed_department(self):
        ci = CMDBService.create_ci(
            user=self.manager_a,
            ci_type=self.ci_type,
            name="switch-01",
            identifier="SRV-003",
            department=self.dept_a,
        )
        self.assertEqual(ci.department, self.dept_a)

    def test_administrator_unrestricted(self):
        ci = CMDBService.create_ci(
            user=self.admin,
            ci_type=self.ci_type,
            name="switch-02",
            identifier="SRV-004",
            department=self.dept_b,
        )
        self.assertEqual(ci.department, self.dept_b)

    def test_self_relationship_rejected_by_service(self):
        with self.assertRaises(ValidationError):
            CMDBService.add_relationship(
                self.a, self.a, CIRelationship.TYPE_DEPENDS_ON
            )

    def test_duplicate_relationship_rejected_by_service(self):
        CMDBService.add_relationship(
            self.a, self.b, CIRelationship.TYPE_DEPENDS_ON
        )
        with self.assertRaises(ValidationError):
            CMDBService.add_relationship(
                self.a, self.b, CIRelationship.TYPE_DEPENDS_ON
            )

    def test_invalid_relationship_type_rejected(self):
        with self.assertRaises(ValidationError):
            CMDBService.add_relationship(self.a, self.b, "not_a_real_type")

    def test_same_pair_different_type_is_allowed(self):
        CMDBService.add_relationship(
            self.a, self.b, CIRelationship.TYPE_DEPENDS_ON
        )
        CMDBService.add_relationship(
            self.a, self.b, CIRelationship.TYPE_CONNECTS_TO
        )
        self.assertEqual(
            CIRelationship.objects.filter(source=self.a, target=self.b).count(),
            2,
        )

    def test_remove_relationship(self):
        relationship = CMDBService.add_relationship(
            self.a, self.b, CIRelationship.TYPE_HOSTS
        )
        CMDBService.remove_relationship(relationship)
        self.assertFalse(
            CIRelationship.objects.filter(pk=relationship.pk).exists()
        )

    def test_link_and_unlink_ticket(self):
        ticket = Ticket.objects.create(title="x", description="x")
        CMDBService.link_ticket(self.a, ticket)
        self.assertIn(ticket, self.a.tickets.all())

        CMDBService.unlink_ticket(self.a, ticket)
        self.assertNotIn(ticket, self.a.tickets.all())

    def test_link_and_unlink_change(self):
        change = ChangeService.create_change(
            self.manager_a, title="x", description="x"
        )
        CMDBService.link_change(self.a, change)
        self.assertIn(change, self.a.changes.all())

        CMDBService.unlink_change(self.a, change)
        self.assertNotIn(change, self.a.changes.all())

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            CMDBService.change_status(self.a, "not_a_real_status")


class ConfigurationItemVisibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ci_type = ConfigurationItemType.objects.create(name="Server")
        self.dept = Department.objects.create(name="IT")
        self.other_dept = Department.objects.create(name="Finance")

        self.in_service = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-01", identifier="SRV-001",
            department=self.dept, status=ConfigurationItem.STATUS_IN_SERVICE,
        )
        self.retired = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-old", identifier="SRV-002",
            department=self.dept, status=ConfigurationItem.STATUS_RETIRED,
        )

        requester_group = Group.objects.create(name="Requester")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_configurationitem")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_configurationitem")

        self.requester = User.objects.create_user(
            username="cmdb_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.technician = User.objects.create_user(
            username="cmdb_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="cmdb_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="cmdb_other_manager", password="password123"
        )
        self.other_manager.groups.add(manager_group)
        self.other_dept.managers.add(self.other_manager)

        self.admin = User.objects.create_superuser(
            username="cmdb_admin", password="password123", email="a@test.com"
        )

    def test_anonymous_sees_nothing(self):
        self.assertEqual(
            get_configuration_item_queryset(AnonymousUser()).count(), 0
        )

    def test_requester_has_no_visibility(self):
        self.assertEqual(
            get_configuration_item_queryset(self.requester).count(), 0
        )

    def test_technician_sees_in_service_but_not_retired(self):
        qs = get_configuration_item_queryset(self.technician)
        self.assertIn(self.in_service, qs)
        self.assertNotIn(self.retired, qs)

    def test_manager_sees_department_items_including_retired(self):
        qs = get_configuration_item_queryset(self.manager)
        self.assertIn(self.in_service, qs)
        self.assertIn(self.retired, qs)

    def test_unrelated_manager_does_not_see_department_items(self):
        qs = get_configuration_item_queryset(self.other_manager)
        self.assertNotIn(self.in_service, qs)

    def test_administrator_sees_everything(self):
        qs = get_configuration_item_queryset(self.admin)
        self.assertEqual(qs.count(), 2)

    def test_requester_gets_403_on_list(self):
        self.client.login(username="cmdb_requester", password="password123")
        response = self.client.get(reverse("service_desk:cmdb_item_list"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:cmdb_item_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_technician_gets_404_for_retired_item_detail(self):
        self.client.login(username="cmdb_technician", password="password123")
        response = self.client.get(
            reverse("service_desk:cmdb_item_detail", args=[self.retired.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_unrelated_manager_gets_404_not_403_on_detail(self):
        self.client.login(
            username="cmdb_other_manager", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:cmdb_item_detail", args=[self.in_service.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_relationship_queryset_follows_source_visibility(self):
        target = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="db-01", identifier="SRV-003",
            department=self.other_dept,
        )
        relationship = CIRelationship.objects.create(
            source=self.retired,
            target=target,
            relationship_type=CIRelationship.TYPE_DEPENDS_ON,
        )

        # Technician can't see the retired source -> can't see the edge
        self.assertNotIn(
            relationship, get_ci_relationship_queryset(self.technician)
        )
        # The managing manager of the source's department can
        self.assertIn(
            relationship, get_ci_relationship_queryset(self.manager)
        )


class CMDBWorkflowViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ci_type = ConfigurationItemType.objects.create(name="Server")
        self.dept = Department.objects.create(name="IT")

        manager_group = Group.objects.create(name="Manager")
        _grant(
            manager_group,
            "view_configurationitem",
            "add_configurationitem",
            "change_configurationitem",
            "view_ticket",
            "view_change",
            "add_change",
            "change_change",
        )

        self.manager = User.objects.create_user(
            username="cmdb_wf_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.ticket = Ticket.objects.create(
            title="Server down", description="x", department=self.dept,
            created_by=self.manager,
        )

    def test_full_lifecycle_through_real_views(self):
        self.client.login(username="cmdb_wf_manager", password="password123")

        create_response = self.client.post(
            reverse("service_desk:cmdb_item_create"),
            {
                "ci_type": self.ci_type.pk,
                "name": "app-01",
                "identifier": "SRV-100",
                "status": "in_service",
                "criticality": "high",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        source = ConfigurationItem.objects.get(identifier="SRV-100")

        create_response_2 = self.client.post(
            reverse("service_desk:cmdb_item_create"),
            {
                "ci_type": self.ci_type.pk,
                "name": "db-01",
                "identifier": "SRV-101",
                "status": "in_service",
                "criticality": "critical",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(create_response_2.status_code, 302)
        target = ConfigurationItem.objects.get(identifier="SRV-101")

        relationship_response = self.client.post(
            reverse("service_desk:cmdb_relationship_add", args=[source.pk]),
            {"target_id": target.pk, "relationship_type": "depends_on"},
        )
        self.assertEqual(relationship_response.status_code, 302)
        self.assertTrue(
            CIRelationship.objects.filter(source=source, target=target).exists()
        )

        link_ticket_response = self.client.post(
            reverse("service_desk:cmdb_link_ticket", args=[source.pk]),
            {"ticket_id": self.ticket.pk},
        )
        self.assertEqual(link_ticket_response.status_code, 302)
        self.assertIn(self.ticket, source.tickets.all())

        unlink_response = self.client.post(
            reverse(
                "service_desk:cmdb_unlink_ticket",
                args=[source.pk, self.ticket.pk],
            )
        )
        self.assertEqual(unlink_response.status_code, 302)
        source.refresh_from_db()
        self.assertNotIn(self.ticket, source.tickets.all())

    def test_self_relationship_via_view_is_rejected(self):
        self.client.login(username="cmdb_wf_manager", password="password123")
        ci = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-02", identifier="SRV-200",
            department=self.dept,
        )

        response = self.client.post(
            reverse("service_desk:cmdb_relationship_add", args=[ci.pk]),
            {"target_id": ci.pk, "relationship_type": "depends_on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CIRelationship.objects.count(), 0)

    def test_create_rejects_get(self):
        self.client.login(username="cmdb_wf_manager", password="password123")
        # GET is allowed on create (renders the form) — POST-only
        # applies to the mutation actions instead.
        ci = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-03", identifier="SRV-300",
            department=self.dept,
        )
        response = self.client.get(
            reverse("service_desk:cmdb_link_ticket", args=[ci.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_link_ticket_requires_csrf_token(self):
        ci = ConfigurationItem.objects.create(
            ci_type=self.ci_type, name="app-04", identifier="SRV-400",
            department=self.dept,
        )
        client = Client(enforce_csrf_checks=True)
        client.login(username="cmdb_wf_manager", password="password123")
        response = client.post(
            reverse("service_desk:cmdb_link_ticket", args=[ci.pk]),
            {"ticket_id": self.ticket.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(self.ticket, ci.tickets.all())

    def test_anonymous_create_redirects_to_login(self):
        response = self.client.post(
            reverse("service_desk:cmdb_item_create"),
            {"name": "x"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
