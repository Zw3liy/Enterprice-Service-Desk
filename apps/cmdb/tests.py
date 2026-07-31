from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.cmdb.models import ConfigurationItem
from apps.cmdb.services import CMDBService
from apps.service_desk.models import Company

User = get_user_model()


class CMDBServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="CMDB Co", slug="cmdb-co")

    def test_upsert_link_impact(self):
        app = CMDBService.upsert_ci(
            self.company, name="Billing API", ci_class_code="application"
        )
        db = CMDBService.upsert_ci(
            self.company, name="Billing DB", ci_class_code="database"
        )
        CMDBService.link(app, db, relation_type="depends_on")
        tree = CMDBService.impact_tree(app)
        self.assertEqual(tree["ci_id"], app.ci_id)
        self.assertEqual(len(tree["downstream"]), 1)

    def test_discovery(self):
        result = CMDBService.ingest_discovery(
            self.company,
            {"hostname": "web-01", "ip_address": "10.0.0.5", "os_name": "Ubuntu Server"},
        )
        self.assertTrue(result.processed)
        self.assertIsNotNone(result.matched_ci)
        self.assertTrue(
            ConfigurationItem.objects.filter(company=self.company, name="web-01").exists()
        )


class CMDBUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="CMDB UI", slug="cmdb-ui")
        self.user = User.objects.create_user(
            username="cmdbui", password="pass12345", is_staff=True
        )
        self.client = Client()
        self.client.login(username="cmdbui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()
        CMDBService.upsert_ci(self.company, name="Edge Router", ci_id="NET-EDGE-1", ci_class_code="network")

    def test_list(self):
        res = self.client.get(reverse("cmdb_app:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Edge Router")