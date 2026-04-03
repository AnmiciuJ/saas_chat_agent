import hashlib
import json
import urllib.error
import urllib.request

import config


def _synthetic_vector(text, dim):
    seed = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
    v = []
    for i in range(dim):
        b = seed[i % len(seed)]
        v.append((b / 127.5) - 1.0)
    return v


def embed_query_text(text, model_key=None, dimension=1536, timeout=120):
    base = (config.EMBEDDING_API_BASE_URL or "").strip().rstrip("/")
    if not base:
        return _synthetic_vector(text, dimension)
    model = (model_key or config.EMBEDDING_DEFAULT_MODEL or "").strip() or "local"
    raw = embed_texts([text], model_key=model, timeout=timeout)
    data = raw.get("data") or []
    if not data:
        raise RuntimeError("embedding_empty")
    data.sort(key=lambda x: x.get("index", 0))
    return data[0]["embedding"]


def embed_texts(texts, model_key=None, timeout=120):
    base = (config.EMBEDDING_API_BASE_URL or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("embedding_not_configured")
    model = (model_key or config.EMBEDDING_DEFAULT_MODEL or "").strip()
    if not model:
        raise RuntimeError("embedding_model_required")
    url = base + "/v1/embeddings"
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = (config.EMBEDDING_API_KEY or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"embedding_http_{e.code}:{err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"embedding_network:{e.reason}") from e
    return json.loads(raw)
