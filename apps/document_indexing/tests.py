from django.test import TestCase

from apps.document_indexing.services import DocumentIndexService
from apps.service_desk.models import Company, KnowledgeArticle


class DocumentIndexTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="IdxCo", slug="idx-co")
        self.article = KnowledgeArticle.objects.create(
            company=self.company,
            title="Reset VPN password",
            slug="reset-vpn-password",
            body="Steps to reset corporate VPN credentials safely.",
            is_published=True,
        )

    def test_index_and_search(self):
        DocumentIndexService.index_knowledge_article(self.article)
        results = DocumentIndexService.search(self.company, "vpn password")
        self.assertTrue(results)
        self.assertEqual(results[0]["source_type"], "knowledge")
