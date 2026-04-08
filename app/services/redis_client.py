"""
Redis 客户端单例。

提供全局共享的 Redis 连接实例，所有业务层通过此模块获取。
"""

import redis

import config

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """获取 Redis 连接实例（惰性初始化）。"""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            config.REDIS_URL,
            decode_responses=True,
        )
    return _client
