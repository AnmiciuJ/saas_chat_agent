import config
from django.utils import timezone

from app.apps.knowledge_base.models import KnowledgeBase, KnowledgeEntry, KnowledgeEntryChunk
from offline_service.indexing import delete_ids, delete_prefix, upsert_points

from .chunking import split_text
from .ingestion import _embed_batches


def _point_id_entry(tenant_id, kb_id, entry_id, chunk_index):
    s = f"v1e:{tenant_id}:{kb_id}:{entry_id}:{chunk_index}"
    return s[:128]


def run_knowledge_entry_ingestion(entry_id):
    entry = KnowledgeEntry.objects.select_related(
        "knowledge_base",
        "knowledge_base__embedding_model",
        "tenant",
    ).get(pk=entry_id)
    if entry.status != KnowledgeEntry.Status.PUBLISHED:
        return
    kb = entry.knowledge_base
    tenant = entry.tenant
    if kb.status != KnowledgeBase.Status.ACTIVE:
        return
    text = (entry.body or "").strip()
    if not text:
        prefix = f"v1e:{tenant.id}:{kb.id}:{entry.id}:"
        old = list(KnowledgeEntryChunk.objects.filter(knowledge_entry=entry))
        delete_ids([c.vector_point_id for c in old if c.vector_point_id])
        KnowledgeEntryChunk.objects.filter(knowledge_entry=entry).delete()
        delete_prefix(prefix)
        return
    size = int(config.INGEST_CHUNK_SIZE)
    overlap = int(config.INGEST_CHUNK_OVERLAP)
    parts = split_text(text, size, overlap)
    if not parts:
        return
    em = kb.embedding_model
    dim = em.vector_dimension if em else 1536
    mk = em.model_key if em else (config.EMBEDDING_DEFAULT_MODEL or "local")
    emb_key = kb.embedding_model_key or ""
    resolved_snapshot_id = entry.snapshot_id or kb.current_snapshot_id
    prefix = f"v1e:{tenant.id}:{kb.id}:{entry.id}:"
    old_chunks = list(KnowledgeEntryChunk.objects.filter(knowledge_entry=entry))
    delete_ids([c.vector_point_id for c in old_chunks if c.vector_point_id])
    KnowledgeEntryChunk.objects.filter(knowledge_entry=entry).delete()
    delete_prefix(prefix)
    vectors = _embed_batches(parts, mk, dim)
    if len(vectors) != len(parts):
        return
    now = timezone.now()
    ups = []
    n = len(parts)
    for idx, (chunk_text, vec) in enumerate(zip(parts, vectors)):
        pid = _point_id_entry(tenant.id, kb.id, entry.id, idx)
        kec = KnowledgeEntryChunk.objects.create(
            tenant=tenant,
            knowledge_entry=entry,
            chunk_index=idx,
            text_content=chunk_text,
            char_count=len(chunk_text),
            vector_point_id=pid,
            embedding_model_key=emb_key[:128] if emb_key else None,
            snapshot_id=resolved_snapshot_id,
            metadata={"source_kind": "knowledge_entry_chunk"},
            created_at=now,
        )
        ups.append(
            {
                "id": pid,
                "vector": vec,
                "metadata": {
                    "tenant_id": tenant.id,
                    "knowledge_base_id": kb.id,
                    "snapshot_id": resolved_snapshot_id,
                    "knowledge_entry_id": entry.id,
                    "chunk_id": kec.id,
                    "chunk_index": idx,
                    "text": chunk_text[:2000],
                    "embedding_model_key": emb_key,
                    "source_kind": "knowledge_entry_chunk",
                },
            }
        )
    upsert_points(ups)


def clear_knowledge_entry_index(entry_id):
    entry = KnowledgeEntry.objects.get(pk=entry_id)
    prefix = f"v1e:{entry.tenant_id}:{entry.knowledge_base_id}:{entry.id}:"
    old = list(KnowledgeEntryChunk.objects.filter(knowledge_entry=entry))
    delete_ids([c.vector_point_id for c in old if c.vector_point_id])
    KnowledgeEntryChunk.objects.filter(knowledge_entry=entry).delete()
    delete_prefix(prefix)
