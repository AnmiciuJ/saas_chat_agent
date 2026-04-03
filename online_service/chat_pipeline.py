import config

from online_service.llm import chat_completion


def stub_reply_when_no_llm(user_text, retrieval_payload):
    base = (config.LLM_API_BASE_URL or "").strip()
    if base:
        return None
    items = (retrieval_payload or {}).get("items") or []
    if not items:
        return "（未配置语言模型接口，且无检索上下文，此为占位回复。）"
    parts = []
    for it in items[:5]:
        t = (it.get("text") or "")[:500]
        if t:
            parts.append(t)
    ctx = "\n---\n".join(parts)
    return f"（未配置语言模型接口；以下为检索到的片段摘要。）\n\n{ctx}\n\n用户问题：{user_text[:2000]}"


def build_llm_messages(history_messages, user_content, retrieval_payload):
    sys_parts = ["你是协助用户的助手，请基于给定上下文与对话历史作答。"]
    items = (retrieval_payload or {}).get("items") or []
    if items:
        sys_parts.append("检索到的片段：")
        for it in items[:12]:
            sys_parts.append((it.get("text") or "")[:3500])
    system_text = "\n".join(sys_parts)[:120000]
    out = [{"role": "system", "content": system_text}]
    for m in history_messages:
        r = m.get("role")
        c = m.get("content") or ""
        if r == "user":
            out.append({"role": "user", "content": c})
        elif r == "assistant":
            out.append({"role": "assistant", "content": c})
    out.append({"role": "user", "content": user_content})
    return out


def parse_llm_content(raw):
    try:
        return raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def parse_usage(raw):
    u = raw.get("usage") or {}
    return u.get("prompt_tokens"), u.get("completion_tokens")


def run_assistant_generation(user_text, retrieval_payload, history_messages, model_key):
    stub = stub_reply_when_no_llm(user_text, retrieval_payload)
    if stub is not None:
        return {
            "assistant_text": stub,
            "prompt_tokens": None,
            "completion_tokens": None,
            "error": None,
            "detail": None,
        }
    try:
        msgs = build_llm_messages(history_messages, user_text, retrieval_payload)
        raw = chat_completion(msgs, model_key=model_key, temperature=0.7)
        assistant_text = parse_llm_content(raw)
        pt, ct = parse_usage(raw)
    except Exception as e:
        return {
            "assistant_text": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "error": "llm_failed",
            "detail": str(e)[:2000],
        }
    if not assistant_text:
        assistant_text = "（模型返回空内容。）"
    return {
        "assistant_text": assistant_text,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "error": None,
        "detail": None,
    }
