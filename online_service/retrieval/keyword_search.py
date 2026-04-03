from app.apps.documents.models import DocumentChunk
from app.apps.knowledge_base.models import KnowledgeEntry, KnowledgeEntryChunk


def search_document_chunks(tenant_id, knowledge_base_id, query, limit=40):
    q = (query or "").strip()
    if not q:
        return []
    return list(
        DocumentChunk.objects.filter(
            tenant_id=tenant_id,
            document__knowledge_base_id=knowledge_base_id,
        )
        .filter(text_content__icontains=q[:512])
        .order_by("-id")[:limit]
    )


def search_knowledge_entry_chunks(tenant_id, knowledge_base_id, query, limit=40):
    q = (query or "").strip()
    if not q:
        return []
    return list(
        KnowledgeEntryChunk.objects.filter(
            tenant_id=tenant_id,
            knowledge_entry__knowledge_base_id=knowledge_base_id,
            knowledge_entry__status=KnowledgeEntry.Status.PUBLISHED,
        )
        .filter(text_content__icontains=q[:512])
        .order_by("-id")[:limit]
    )
