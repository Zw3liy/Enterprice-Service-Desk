from __future__ import annotations

import re
from collections import Counter

from django.db.models import Q

from apps.document_indexing.models import IndexedDocument
from apps.service_desk.models import KnowledgeArticle, Ticket


TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


class DocumentIndexService:
    @staticmethod
    def tokenize(text: str) -> list[str]:
        return sorted(set(TOKEN_RE.findall((text or "").lower())))

    @classmethod
    def upsert(
        cls,
        company,
        *,
        source_type: str,
        source_id: str,
        title: str,
        body: str = "",
        url: str = "",
        metadata: dict | None = None,
    ) -> IndexedDocument:
        tokens = cls.tokenize(f"{title}\n{body}")
        doc, _ = IndexedDocument.objects.update_or_create(
            company=company,
            source_type=source_type,
            source_id=str(source_id),
            defaults={
                "title": title[:255],
                "body": body,
                "url": url,
                "tokens": tokens,
                "metadata": metadata or {},
                "is_active": True,
            },
        )
        return doc

    @classmethod
    def index_knowledge_article(cls, article: KnowledgeArticle) -> IndexedDocument:
        return cls.upsert(
            article.company,
            source_type="knowledge",
            source_id=str(article.pk),
            title=article.title,
            body=f"{article.summary}\n{article.body}",
            url=f"/knowledge/{article.slug}/",
            metadata={"slug": article.slug, "published": article.is_published},
        )

    @classmethod
    def index_ticket(cls, ticket: Ticket) -> IndexedDocument:
        return cls.upsert(
            ticket.company,
            source_type="ticket",
            source_id=str(ticket.pk),
            title=f"{ticket.ticket_number} {ticket.title}",
            body=ticket.description or "",
            url=f"/tickets/{ticket.pk}/",
            metadata={"ticket_number": ticket.ticket_number},
        )

    @classmethod
    def reindex_company(cls, company) -> dict:
        k = 0
        for article in KnowledgeArticle.objects.filter(company=company, is_published=True):
            cls.index_knowledge_article(article)
            k += 1
        t = 0
        for ticket in Ticket.objects.filter(company=company).order_by("-id")[:500]:
            cls.index_ticket(ticket)
            t += 1
        return {"knowledge": k, "tickets": t}

    @classmethod
    def search(cls, company, query: str, *, limit: int = 25) -> list[dict]:
        q_tokens = cls.tokenize(query)
        if not q_tokens:
            return []
        qs = IndexedDocument.objects.filter(company=company, is_active=True)
        # rough filter using title/body contains first token
        qs = qs.filter(
            Q(title__icontains=q_tokens[0])
            | Q(body__icontains=q_tokens[0])
            | Q(tokens__icontains=q_tokens[0])
        )[:200]
        scored = []
        qset = set(q_tokens)
        for doc in qs:
            overlap = len(qset.intersection(set(doc.tokens or [])))
            if overlap <= 0 and q_tokens[0] not in (doc.title or "").lower():
                continue
            score = overlap * 10
            title_l = (doc.title or "").lower()
            for tok in q_tokens:
                if tok in title_l:
                    score += 5
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": doc.pk,
                "source_type": doc.source_type,
                "source_id": doc.source_id,
                "title": doc.title,
                "url": doc.url,
                "score": score,
                "metadata": doc.metadata,
            }
            for score, doc in scored[:limit]
        ]
