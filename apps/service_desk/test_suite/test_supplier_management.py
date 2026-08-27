from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.db import IntegrityError

from apps.service_desk.models import Department, Supplier
from apps.service_desk.forms.supplier_forms import SupplierCreateForm
from apps.service_desk.services.supplier_service import SupplierService
from apps.service_desk.security.policies import get_supplier_queryset


class SupplierManagementTests(TestCase):

    def setUp(self):

        self.client = Client()

        # Departments
        self.it = Department.objects.create(name="IT")

        # Users
        self.admin = User.objects.create_superuser(
            username="admin",
            password="password123",
            email="admin@test.com",
        )

        self.manager = User.objects.create_user(
            username="manager",
            password="password123",
        )

        # Groups and permissions will be created after migrations
        manager_group = Group.objects.create(name="Manager")
        self.manager.groups.add(manager_group)


    def test_supplier_model_unique_name(self):

        Supplier.objects.create(name="Acme", department=self.it)

        with self.assertRaises(IntegrityError):
            # unique constraint at DB level
            Supplier.objects.create(name="Acme", department=self.it)


    def test_supplier_create_form_validation(self):

        form = SupplierCreateForm(data={})
        self.assertFalse(form.is_valid())

        form = SupplierCreateForm(data={"name": "Acme"})
        self.assertTrue(form.is_valid())


    def test_supplier_service_create_and_update(self):

        sup = SupplierService.create_supplier(name="Beta", department=self.it)
        self.assertEqual(sup.name, "Beta")

        # update only when changed
        SupplierService.update_supplier(sup, name="Beta")
        SupplierService.update_supplier(sup, name="Beta Corp")
        sup.refresh_from_db()
        self.assertEqual(sup.name, "Beta Corp")


    def test_role_based_supplier_visibility(self):

        # manager manages IT
        self.it.managers.add(self.manager)

        # supplier in IT
        s = Supplier.objects.create(name="Visible Co", department=self.it)

        # admin sees all
        qs_admin = get_supplier_queryset(self.admin)
        self.assertIn(s, qs_admin)

        # manager sees department supplier
        qs_mgr = get_supplier_queryset(self.manager)
        self.assertIn(s, qs_mgr)


    def test_supplier_list_and_detail_access(self):

        # create supplier
        s = Supplier.objects.create(name="ViewCo", department=self.it)

        # create and assign permissions for Manager group
        manager_group = Group.objects.get(name="Manager")
        view_perm = Permission.objects.get(codename="view_supplier")
        add_perm = Permission.objects.get(codename="add_supplier")
        manager_group.permissions.add(view_perm, add_perm)

        # manager should be allowed to access list and create
        # manager manages IT department so detail should be visible
        self.it.managers.add(self.manager)
        self.client.login(username="manager", password="password123")

        resp = self.client.get("/suppliers/")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/suppliers/new/")
        self.assertEqual(resp.status_code, 200)

        # detail
        resp = self.client.get(f"/suppliers/{s.pk}/")
        self.assertEqual(resp.status_code, 200)

        # user without perms
        noperms = User.objects.create_user(username="noperms", password="password123")
        self.client.login(username="noperms", password="password123")
        resp = self.client.get("/suppliers/")
        self.assertEqual(resp.status_code, 403)


class SupplierWorkflowTests(TestCase):
    """
    ITSM-08 completion: update, active/inactive lifecycle,
    department scoping and list filtering.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        perms = Permission.objects.filter(
            codename__in=[
                "view_supplier",
                "add_supplier",
                "change_supplier",
            ]
        )

        manager_group = Group.objects.create(name="Manager")
        manager_group.permissions.set(perms)

        self.manager = User.objects.create_user(
            username="it-manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.it.managers.add(self.manager)

        self.hr_manager = User.objects.create_user(
            username="hr-manager", password="password123"
        )
        self.hr_manager.groups.add(manager_group)
        self.hr.managers.add(self.hr_manager)

        self.admin = User.objects.create_superuser(
            username="supplier-admin",
            password="password123",
            email="a@example.com",
        )

        self.it_supplier = Supplier.objects.create(
            name="IT Vendor", department=self.it
        )
        self.hr_supplier = Supplier.objects.create(
            name="HR Vendor", department=self.hr
        )

    # ------------------------------------------------------------------
    # Service layer
    # ------------------------------------------------------------------

    def test_manager_cannot_create_supplier_outside_managed_department(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            SupplierService.create_supplier(
                user=self.manager,
                name="Foreign Vendor",
                department=self.hr,
            )

        self.assertFalse(
            Supplier.objects.filter(name="Foreign Vendor").exists()
        )

    def test_manager_cannot_create_unscoped_supplier(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            SupplierService.create_supplier(
                user=self.manager,
                name="Orphan Vendor",
                department=None,
            )

    def test_administrator_may_create_any_supplier(self):
        supplier = SupplierService.create_supplier(
            user=self.admin,
            name="Global Vendor",
            department=self.hr,
        )
        self.assertEqual(supplier.department, self.hr)

    def test_deactivate_and_activate_lifecycle(self):
        from django.core.exceptions import ValidationError

        SupplierService.deactivate_supplier(
            self.it_supplier, user=self.manager
        )
        self.it_supplier.refresh_from_db()
        self.assertFalse(self.it_supplier.is_active)

        with self.assertRaises(ValidationError):
            SupplierService.deactivate_supplier(
                self.it_supplier, user=self.manager
            )

        SupplierService.activate_supplier(
            self.it_supplier, user=self.manager
        )
        self.it_supplier.refresh_from_db()
        self.assertTrue(self.it_supplier.is_active)

        with self.assertRaises(ValidationError):
            SupplierService.activate_supplier(
                self.it_supplier, user=self.manager
            )

    def test_update_cannot_move_supplier_to_unmanaged_department(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            SupplierService.update_supplier(
                self.it_supplier,
                user=self.manager,
                department=self.hr,
            )

        self.it_supplier.refresh_from_db()
        self.assertEqual(self.it_supplier.department, self.it)

    # ------------------------------------------------------------------
    # Form scoping
    # ------------------------------------------------------------------

    def test_form_department_choices_are_scoped_for_manager(self):
        form = SupplierCreateForm(user=self.manager)
        choices = list(form.fields["department"].queryset)

        self.assertEqual(choices, [self.it])

    def test_form_department_choices_unrestricted_for_administrator(self):
        form = SupplierCreateForm(user=self.admin)
        self.assertEqual(form.fields["department"].queryset.count(), 2)

    # ------------------------------------------------------------------
    # Views / RBAC
    # ------------------------------------------------------------------

    def test_anonymous_supplier_access_redirects_to_login(self):
        response = self.client.get("/suppliers/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_manager_cannot_open_another_departments_supplier(self):
        self.client.login(username="it-manager", password="password123")

        response = self.client.get(f"/suppliers/{self.hr_supplier.pk}/")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/suppliers/{self.hr_supplier.pk}/edit/")
        self.assertEqual(response.status_code, 404)

    def test_manager_cannot_deactivate_another_departments_supplier(self):
        self.client.login(username="it-manager", password="password123")

        response = self.client.post(
            f"/suppliers/{self.hr_supplier.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 404)

        self.hr_supplier.refresh_from_db()
        self.assertTrue(self.hr_supplier.is_active)

    def test_manager_updates_own_supplier_through_the_view(self):
        self.client.login(username="it-manager", password="password123")

        response = self.client.post(
            f"/suppliers/{self.it_supplier.pk}/edit/",
            {
                "name": "IT Vendor Renamed",
                "description": "Updated",
                "contact_name": "Jane",
                "contact_email": "jane@example.com",
                "phone": "",
                "department": self.it.pk,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.it_supplier.refresh_from_db()
        self.assertEqual(self.it_supplier.name, "IT Vendor Renamed")

    def test_deactivate_view_toggles_lifecycle(self):
        self.client.login(username="it-manager", password="password123")

        response = self.client.post(
            f"/suppliers/{self.it_supplier.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 302)

        self.it_supplier.refresh_from_db()
        self.assertFalse(self.it_supplier.is_active)

        self.client.post(f"/suppliers/{self.it_supplier.pk}/activate/")
        self.it_supplier.refresh_from_db()
        self.assertTrue(self.it_supplier.is_active)

    def test_lifecycle_actions_require_change_permission(self):
        view_only = Group.objects.create(name="SupplierViewer")
        view_only.permissions.set(
            Permission.objects.filter(codename="view_supplier")
        )

        viewer = User.objects.create_user(
            username="viewer", password="password123"
        )
        viewer.groups.add(view_only)
        self.it.managers.add(viewer)

        self.client.login(username="viewer", password="password123")

        response = self.client.post(
            f"/suppliers/{self.it_supplier.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 403)

    def test_list_filters_and_counts_are_scoped(self):
        Supplier.objects.create(
            name="Retired IT Vendor", department=self.it, is_active=False
        )

        self.client.login(username="it-manager", password="password123")

        response = self.client.get("/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total"], 2)
        self.assertEqual(response.context["stats"]["inactive"], 1)
        self.assertNotContains(response, "HR Vendor")

        response = self.client.get("/suppliers/?status=inactive")
        names = [s.name for s in response.context["suppliers"]]
        self.assertEqual(names, ["Retired IT Vendor"])

        response = self.client.get("/suppliers/?q=Retired")
        names = [s.name for s in response.context["suppliers"]]
        self.assertEqual(names, ["Retired IT Vendor"])

    def test_create_view_rejects_out_of_scope_department(self):
        self.client.login(username="it-manager", password="password123")

        response = self.client.post(
            "/suppliers/new/",
            {
                "name": "Sneaky Vendor",
                "description": "",
                "contact_name": "",
                "contact_email": "",
                "phone": "",
                "department": self.hr.pk,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Supplier.objects.filter(name="Sneaky Vendor").exists()
        )
