import math

_store = {}


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search(query_vector, tenant_id, knowledge_base_id, top_k=10, snapshot_id=None):
    scored = []
    for pid, entry in _store.items():
        meta = entry.get("metadata") or {}
        if meta.get("tenant_id") != tenant_id:
            continue
        if meta.get("knowledge_base_id") != knowledge_base_id:
            continue
        if snapshot_id is not None and meta.get("snapshot_id") != snapshot_id:
            continue
        vec = entry.get("vector")
        if not vec:
            continue
        if len(vec) != len(query_vector):
            continue
        s = _cosine(query_vector, vec)
        scored.append((s, pid, meta))
    scored.sort(key=lambda x: -x[0])
    return scored[: max(1, top_k)]


def upsert_points(points):
    for p in points:
        pid = p["id"]
        _store[pid] = {"vector": p["vector"], "metadata": dict(p.get("metadata") or {})}


def delete_ids(ids):
    for i in ids:
        if i:
            _store.pop(i, None)


def delete_prefix(prefix):
    keys = [k for k in _store if str(k).startswith(prefix)]
    for k in keys:
        _store.pop(k, None)
