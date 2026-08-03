from django.test import TestCase
from apps.service_catalog.services import ServiceCatalogService
from apps.service_desk.models import Company, Department, RequestType

class CatalogTests(TestCase):
    def test_list(self):
        c=Company.objects.create(name="C", slug="cat-c")
        d=Department.objects.create(company=c,name="IT",code="it")
        RequestType.objects.create(department=d,name="Access",code="access")
        self.assertEqual(ServiceCatalogService.list_items(c).count(),1)
