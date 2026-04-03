import json
import urllib.error
import urllib.request

import config


def chat_completion(messages, model_key=None, temperature=0.7, timeout=120):
    base = (config.LLM_API_BASE_URL or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("llm_not_configured")
    model = (model_key or config.LLM_DEFAULT_MODEL or "").strip()
    if not model:
        raise RuntimeError("model_required")
    url = base + "/v1/chat/completions"
    body = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature}
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = (config.LLM_API_KEY or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"llm_http_{e.code}:{err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"llm_network:{e.reason}") from e
    return json.loads(raw)
