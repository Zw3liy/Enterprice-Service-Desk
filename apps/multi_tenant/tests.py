from django.test import TestCase

from apps.multi_tenant.models import TenantDomain, TenantSettings
from apps.multi_tenant.services import TenantService
from apps.service_desk.models import Company, Status


class MultiTenantTests(TestCase):
    def test_provision_domain_features(self):
        company = TenantService.provision(
            "Acme Tenant",
            slug="acme-tenant",
            admin_email="admin@acme.test",
            domain="acme.local",
        )
        self.assertTrue(Company.objects.filter(slug="acme-tenant").exists())
        self.assertTrue(Status.objects.filter(company=company).exists())
        self.assertTrue(TenantSettings.objects.filter(company=company).exists())
        self.assertTrue(TenantDomain.objects.filter(domain="acme.local").exists())
        resolved = TenantService.resolve_by_domain("acme.local")
        self.assertEqual(resolved.pk, company.pk)
        self.assertTrue(TenantService.feature_enabled(company, "ai"))
        TenantService.set_feature(company, "ai", False)
        self.assertFalse(TenantService.feature_enabled(company, "ai"))
