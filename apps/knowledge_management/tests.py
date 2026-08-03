from django.test import TestCase
from apps.knowledge_management.services import KnowledgeService
from apps.service_desk.models import Company, KnowledgeArticle

class KMTests(TestCase):
    def test_search(self):
        c=Company.objects.create(name="K", slug="k-m")
        KnowledgeArticle.objects.create(company=c,title="T",slug="t",body="vpn reset",is_published=True)
        self.assertTrue(KnowledgeService.search("vpn", company=c).exists())
