import hashlib

import config
from django.utils import timezone

from app.apps.documents.models import Document, DocumentChunk, IngestionJob
from app.apps.documents.storage import read_object
from app.apps.knowledge_base.models import KnowledgeBaseSnapshot
from offline_service.embedding import embed_texts
from offline_service.indexing import delete_ids, delete_prefix, upsert_points

from .chunking import split_text


def _synthetic_embeddings(texts, dim):
    out = []
    for t in texts:
        seed = hashlib.sha256(t.encode("utf-8", errors="replace")).digest()
        v = []
        for i in range(dim):
            b = seed[i % len(seed)]
            v.append((b / 127.5) - 1.0)
        out.append(v)
    return out


def _embed_batches(texts, model_key, dim):
    base = (config.EMBEDDING_API_BASE_URL or "").strip()
    batch = max(1, int(config.INGEST_EMBED_BATCH_SIZE))
    all_vecs = []
    if base:
        for i in range(0, len(texts), batch):
            part = texts[i : i + batch]
            raw = embed_texts(part, model_key=model_key)
            data = raw.get("data") or []
            data.sort(key=lambda x: x.get("index", 0))
            for item in data:
                all_vecs.append(item["embedding"])
    else:
        for i in range(0, len(texts), batch):
            part = texts[i : i + batch]
            all_vecs.extend(_synthetic_embeddings(part, dim))
    return all_vecs


def _point_id(tenant_id, kb_id, doc_id, chunk_index):
    s = f"v1:{tenant_id}:{kb_id}:{doc_id}:{chunk_index}"
    return s[:128]


def _fail_job(job, doc, msg, parse_failed=False):
    now = timezone.now()
    IngestionJob.objects.filter(pk=job.pk).update(
        status=IngestionJob.Status.FAILED,
        error_detail=msg[:4096],
        finished_at=now,
        updated_at=now,
    )
    u = {"last_error": msg[:4096], "updated_at": now}
    if parse_failed:
        u["parse_status"] = Document.ParseStatus.FAILED
        u["index_status"] = Document.IndexStatus.PENDING
    else:
        u["parse_status"] = Document.ParseStatus.READY
        u["index_status"] = Document.IndexStatus.FAILED
    Document.objects.filter(pk=doc.pk).update(**u)


def run_ingestion_job(job_id):
    job = IngestionJob.objects.select_related(
        "document",
        "document__knowledge_base",
        "document__knowledge_base__embedding_model",
        "tenant",
    ).get(pk=job_id)
    doc = job.document
    kb = doc.knowledge_base
    tenant = doc.tenant
    now = timezone.now()
    IngestionJob.objects.filter(pk=job.pk).update(
        status=IngestionJob.Status.RUNNING,
        started_at=now,
        progress_percent=2,
        worker_task_id=f"sync:{job.pk}",
        updated_at=now,
    )
    Document.objects.filter(pk=doc.pk).update(
        parse_status=Document.ParseStatus.PROCESSING,
        index_status=Document.IndexStatus.PENDING,
        last_error=None,
        updated_at=now,
    )
    try:
        raw = read_object(doc.storage_key)
    except OSError as e:
        _fail_job(job, doc, str(e), parse_failed=True)
        return
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        _fail_job(job, doc, "empty_text", parse_failed=True)
        return
    extra0 = doc.chunk_profile_json or {}
    target_snap = extra0.get("ingest_target_snapshot_id")
    if target_snap is not None:
        if not KnowledgeBaseSnapshot.objects.filter(pk=target_snap, knowledge_base=kb).exists():
            _fail_job(job, doc, "invalid_target_snapshot", parse_failed=True)
            return
    Document.objects.filter(pk=doc.pk).update(
        parse_status=Document.ParseStatus.READY,
        updated_at=timezone.now(),
    )
    IngestionJob.objects.filter(pk=job.pk).update(progress_percent=15, updated_at=timezone.now())
    size = int(config.INGEST_CHUNK_SIZE)
    overlap = int(config.INGEST_CHUNK_OVERLAP)
    parts = split_text(text, size, overlap)
    if not parts:
        _fail_job(job, doc, "no_chunks", parse_failed=True)
        return
    em = kb.embedding_model
    dim = em.vector_dimension if em else 1536
    mk = em.model_key if em else (config.EMBEDDING_DEFAULT_MODEL or "local")
    emb_key = kb.embedding_model_key or ""
    if target_snap is not None:
        resolved_snapshot_id = target_snap
    else:
        resolved_snapshot_id = kb.current_snapshot_id
    prefix = f"v1:{tenant.id}:{kb.id}:{doc.id}:"
    old_chunks = list(DocumentChunk.objects.filter(document=doc))
    old_pids = [c.vector_point_id for c in old_chunks if c.vector_point_id]
    DocumentChunk.objects.filter(document=doc).delete()
    delete_ids(old_pids)
    delete_prefix(prefix)
    IngestionJob.objects.filter(pk=job.pk).update(progress_percent=30, updated_at=timezone.now())
    Document.objects.filter(pk=doc.pk).update(
        index_status=Document.IndexStatus.PROCESSING,
        updated_at=timezone.now(),
    )
    try:
        vectors = _embed_batches(parts, mk, dim)
    except Exception as e:
        _fail_job(job, doc, str(e), parse_failed=False)
        return
    if len(vectors) != len(parts):
        _fail_job(job, doc, "embedding_count_mismatch", parse_failed=False)
        return
    now = timezone.now()
    ups = []
    n = len(parts)
    for idx, (chunk_text, vec) in enumerate(zip(parts, vectors)):
        pid = _point_id(tenant.id, kb.id, doc.id, idx)
        dc = DocumentChunk.objects.create(
            tenant=tenant,
            document=doc,
            chunk_index=idx,
            text_content=chunk_text,
            char_count=len(chunk_text),
            vector_point_id=pid,
            embedding_model_key=emb_key[:128] if emb_key else None,
            snapshot_id=resolved_snapshot_id,
            metadata={"source_kind": "document_chunk"},
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
                    "document_id": doc.id,
                    "chunk_id": dc.id,
                    "chunk_index": idx,
                    "text": chunk_text[:2000],
                    "embedding_model_key": emb_key,
                    "source_kind": "document_chunk",
                },
            }
        )
        pct = 30 + int(60 * (idx + 1) / max(n, 1))
        IngestionJob.objects.filter(pk=job.pk).update(
            progress_percent=min(95, pct), updated_at=timezone.now()
        )
    upsert_points(ups)
    now2 = timezone.now()
    IngestionJob.objects.filter(pk=job.pk).update(
        status=IngestionJob.Status.SUCCEEDED,
        progress_percent=100,
        finished_at=now2,
        updated_at=now2,
    )
    Document.objects.filter(pk=doc.pk).update(
        parse_status=Document.ParseStatus.READY,
        index_status=Document.IndexStatus.READY,
        snapshot_id=resolved_snapshot_id,
        last_error=None,
        updated_at=now2,
    )
