"""
会话短期记忆管理。

使用 Redis 存储会话的最近消息窗口，用于在线链路快速读取上下文。
超出窗口长度的消息自动淘汰。
"""

import json
import logging

from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

WINDOW_SIZE = 20
KEY_TTL_SECONDS = 86400 * 7


def _ctx_key(tenant_id: int, conversation_id: int) -> str:
    return f"tenant:{tenant_id}:conv:{conversation_id}:ctx"


def push_message(
    tenant_id: int,
    conversation_id: int,
    role: str,
    content: str,
) -> None:
    """将一条消息推入短期窗口。"""
    r = get_redis()
    key = _ctx_key(tenant_id, conversation_id)
    entry = json.dumps({"role": role, "content": content}, ensure_ascii=False)
    r.rpush(key, entry)
    r.ltrim(key, -WINDOW_SIZE, -1)
    r.expire(key, KEY_TTL_SECONDS)


def get_window(
    tenant_id: int,
    conversation_id: int,
) -> list[dict[str, str]]:
    """读取短期窗口中的全部消息。"""
    r = get_redis()
    key = _ctx_key(tenant_id, conversation_id)
    raw_list = r.lrange(key, 0, -1)
    return [json.loads(item) for item in raw_list]


def clear_window(tenant_id: int, conversation_id: int) -> None:
    """清空指定会话的短期窗口。"""
    r = get_redis()
    r.delete(_ctx_key(tenant_id, conversation_id))
