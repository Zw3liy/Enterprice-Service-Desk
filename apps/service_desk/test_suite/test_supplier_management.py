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
