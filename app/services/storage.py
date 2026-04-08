"""
对象存储服务。

开发环境使用本地文件系统，生产环境可切换至 MinIO / S3。
存储后端由 config.OBJECT_STORAGE_BACKEND 控制。
"""

import os
import shutil
from pathlib import Path

import config


async def save_file(storage_key: str, content: bytes) -> str:
    """
    将字节内容写入存储，返回实际存储路径。

    参数:
        storage_key: 逻辑存储键（含租户路径前缀）
        content: 文件二进制内容
    """
    if config.OBJECT_STORAGE_BACKEND == "local":
        return _save_local(storage_key, content)
    raise NotImplementedError(f"不支持的存储后端: {config.OBJECT_STORAGE_BACKEND}")


async def read_file(storage_key: str) -> bytes:
    """从存储读取文件内容。"""
    if config.OBJECT_STORAGE_BACKEND == "local":
        return _read_local(storage_key)
    raise NotImplementedError(f"不支持的存储后端: {config.OBJECT_STORAGE_BACKEND}")


def _save_local(storage_key: str, content: bytes) -> str:
    root = Path(config.LOCAL_OBJECT_STORAGE_ROOT)
    target = root / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target)


def _read_local(storage_key: str) -> bytes:
    root = Path(config.LOCAL_OBJECT_STORAGE_ROOT)
    target = root / storage_key
    return target.read_bytes()
