"""
大模型推理客户端。

统一封装对多供应商推理服务的调用，
支持流式（SSE）与非流式两种响应模式。
供应商配置从 config.LLM_PROVIDERS 获取。
"""

import json
import logging
from typing import Any, AsyncGenerator

import httpx

import config

logger = logging.getLogger(__name__)


def _get_provider(provider_key: str | None = None) -> dict:
    key = provider_key or config.LLM_DEFAULT_PROVIDER
    return config.LLM_PROVIDERS[key]


def _build_messages(
    context: dict[str, Any],
    user_message: str,
) -> list[dict[str, str]]:
    """将上下文包组装为 OpenAI 兼容的消息列表。"""
    messages: list[dict[str, str]] = []

    system_prompt = context.get("system_prompt", "")
    retrieval_context = context.get("retrieval_context", [])

    if retrieval_context:
        knowledge_text = "\n\n---\n\n".join(
            item.get("text", "") for item in retrieval_context if item.get("text")
        )
        system_prompt = (
            f"{system_prompt}\n\n"
            f"以下是从知识库中检索到的参考资料，请基于这些内容回答用户问题。"
            f"如果参考资料中没有相关信息，请如实告知。\n\n{knowledge_text}"
        ).strip()

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for msg in context.get("history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


async def stream_completion(
    context: dict[str, Any],
    user_message: str,
    provider_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    向推理服务发送流式请求，逐片段产出生成文本。

    返回的每个片段为纯文本内容（不含 SSE 包装）。
    """
    provider = _get_provider(provider_key)
    messages = _build_messages(context, user_message)

    # DashScope 和 DeepSeek 均兼容 OpenAI 格式的 /chat/completions
    base_url = provider["api_base_url"]
    # 确保 URL 指向 chat completions 端点
    if not base_url.endswith("/chat/completions"):
        base_url = base_url.rstrip("/")
        if "/chat/completions" not in base_url:
            base_url += "/chat/completions"

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            base_url,
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["default_model"],
                "messages": messages,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def complete(
    context: dict[str, Any],
    user_message: str,
    provider_key: str | None = None,
) -> tuple[str, int, int]:
    """
    非流式推理调用。

    返回:
        (回复文本, 提示token数, 生成token数)
    """
    provider = _get_provider(provider_key)
    messages = _build_messages(context, user_message)

    base_url = provider["api_base_url"]
    if not base_url.endswith("/chat/completions"):
        base_url = base_url.rstrip("/")
        if "/chat/completions" not in base_url:
            base_url += "/chat/completions"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            base_url,
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["default_model"],
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
