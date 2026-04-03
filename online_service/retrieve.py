import config

from app.apps.documents.models import DocumentChunk
from app.apps.knowledge_base.models import KnowledgeBase, KnowledgeEntryChunk
from offline_service.embedding import embed_query_text
from offline_service.indexing import search as vector_search
from online_service.retrieval.keyword_search import (
    search_document_chunks,
    search_knowledge_entry_chunks,
)
from online_service.retrieval.rerank import merge_scores


def _ref_key(meta):
    sk = meta.get("source_kind") or "document_chunk"
    cid = meta.get("chunk_id")
    if cid is None:
        return None
    return f"{sk}:{cid}"


def run_retrieval(tenant_id, knowledge_base_id, query_text, top_k=None, snapshot_id=None):
    q = (query_text or "").strip()
    if not q:
        return {
            "rewritten_query": None,
            "pipeline_trace": {
                "vector_hits": 0,
                "keyword_doc_hits": 0,
                "keyword_entry_hits": 0,
                "merged": 0,
            },
            "items": [],
        }
    kb = KnowledgeBase.objects.select_related("embedding_model").get(
        pk=knowledge_base_id,
        tenant_id=tenant_id,
    )
    em = kb.embedding_model
    dim = em.vector_dimension if em else 1536
    mk = em.model_key if em else None
    tk = top_k if top_k is not None else int(getattr(config, "RETRIEVAL_TOP_K", 8))
    tk = max(1, min(tk, 50))
    qv = embed_query_text(q, model_key=mk, dimension=dim)
    vec_hits = vector_search(qv, tenant_id, knowledge_base_id, top_k=tk * 4, snapshot_id=snapshot_id)
    vec_scores = {}
    for score, pid, meta in vec_hits:
        key = _ref_key(meta)
        if key:
            vec_scores[key] = max(vec_scores.get(key, 0.0), float(score))
    kw_doc = search_document_chunks(tenant_id, knowledge_base_id, q, limit=40)
    kw_ent = search_knowledge_entry_chunks(tenant_id, knowledge_base_id, q, limit=40)
    kw_keys = [f"document_chunk:{c.id}" for c in kw_doc] + [
        f"knowledge_entry_chunk:{c.id}" for c in kw_ent
    ]
    ranked = merge_scores(vec_scores, kw_keys)
    items = []
    for key, sc in ranked[:tk]:
        try:
            sk, rid = key.rsplit(":", 1)
            cid = int(rid)
        except ValueError:
            continue
        if sk == "document_chunk":
            try:
                ch = DocumentChunk.objects.select_related("document").get(
                    pk=cid,
                    tenant_id=tenant_id,
                    document__knowledge_base_id=knowledge_base_id,
                )
            except DocumentChunk.DoesNotExist:
                continue
            items.append(
                {
                    "chunk_id": ch.id,
                    "document_id": ch.document_id,
                    "knowledge_entry_id": None,
                    "score": float(sc),
                    "text": ch.text_content[:4000],
                    "source_kind": "document_chunk",
                    "vector_point_id": ch.vector_point_id,
                    "embedding_model_key": ch.embedding_model_key,
                }
            )
        elif sk == "knowledge_entry_chunk":
            try:
                ch = KnowledgeEntryChunk.objects.select_related("knowledge_entry").get(
                    pk=cid,
                    tenant_id=tenant_id,
                    knowledge_entry__knowledge_base_id=knowledge_base_id,
                )
            except KnowledgeEntryChunk.DoesNotExist:
                continue
            items.append(
                {
                    "chunk_id": ch.id,
                    "document_id": None,
                    "knowledge_entry_id": ch.knowledge_entry_id,
                    "score": float(sc),
                    "text": ch.text_content[:4000],
                    "source_kind": "knowledge_entry_chunk",
                    "vector_point_id": ch.vector_point_id,
                    "embedding_model_key": ch.embedding_model_key,
                }
            )
    return {
        "rewritten_query": None,
        "pipeline_trace": {
            "vector_hits": len(vec_hits),
            "keyword_doc_hits": len(kw_doc),
            "keyword_entry_hits": len(kw_ent),
            "merged": len(items),
        },
        "items": items,
    }
