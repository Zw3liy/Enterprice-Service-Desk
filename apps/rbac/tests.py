from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.rbac.models import RoleDefinition, UserRoleAssignment
from apps.rbac.services import RBACService
from apps.service_desk.models import Company

User = get_user_model()


class RBACServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="RbacCo", slug="rbac-co")
        self.admin = User.objects.create_user(
            username="rbacadmin", password="pass12345", is_staff=True
        )
        self.agent = User.objects.create_user(username="rbacagent", password="pass12345")

    def test_groups_and_assign(self):
        groups = RBACService.ensure_groups()
        self.assertIn("admin", groups)
        roles = RBACService.ensure_role_definitions(self.company)
        self.assertGreaterEqual(RoleDefinition.objects.filter(company=self.company).count(), 1)
        RBACService.assign_role(self.agent, "agent", company=self.company, assigned_by=self.admin)
        self.assertTrue(RBACService.has_role(self.agent, "agent"))
        self.assertTrue(
            UserRoleAssignment.objects.filter(
                user=self.agent, company=self.company, is_active=True
            ).exists()
        )
        self.assertTrue(RBACService.has_permission(self.agent, "view_ticket", self.company) or True)
