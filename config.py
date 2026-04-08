"""
全局配置收口模块。

所有运行时参数、环境标识、业务阈值统一在此管理。
应用各层通过 import config 获取配置值，禁止散落硬编码。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ---------- 运行环境 ----------
ENV_MODE: str = os.getenv("ENV_MODE", "development")
DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "on")
APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev-insecure-change-me")
CORS_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# ---------- 关系型数据库（MySQL） ----------
DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "123456")
DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_NAME: str = os.getenv("DB_NAME", "saas_chat_agent")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"mysql+asyncmy://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
)
DATABASE_URL_SYNC: str = os.getenv(
    "DATABASE_URL_SYNC",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
)

# ---------- Redis ----------
REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
REDIS_URL: str = os.getenv(
    "REDIS_URL",
    f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    if REDIS_PASSWORD
    else f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)

# ---------- Celery 异步任务 ----------
CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# ---------- 大语言模型推理 ----------
LLM_PROVIDERS: dict = {
    "deepseek": {
        "api_base_url": "https://api.deepseek.com/chat/completions",
        "api_key": "sk-2bf9b9152dc844aa9b43faa1af42eb2e",
        "default_model": "deepseek-reasoner",
    },
    "qwen3": {
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_key": "sk-29d2082367854da8b812142ee4598dc0",
        "default_model": "qwen3.5-plus",
    },
}
LLM_DEFAULT_PROVIDER: str = os.getenv("LLM_DEFAULT_PROVIDER", "deepseek")

# ---------- 嵌入模型 ----------
EMBEDDING_PROVIDERS: dict = {
    "dashscope": {
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
        "api_key": "sk-29d2082367854da8b812142ee4598dc0",
        "default_model": "text-embedding-v3",
        "vector_dimension": 1024,
    },
}
EMBEDDING_DEFAULT_PROVIDER: str = os.getenv("EMBEDDING_DEFAULT_PROVIDER", "dashscope")

# ---------- 对象存储（开发环境使用本地文件系统） ----------
OBJECT_STORAGE_BACKEND: str = os.getenv("OBJECT_STORAGE_BACKEND", "local")
OBJECT_STORAGE_ENDPOINT: str = os.getenv("OBJECT_STORAGE_ENDPOINT", "http://127.0.0.1:9000")
OBJECT_STORAGE_ACCESS_KEY: str = os.getenv("OBJECT_STORAGE_ACCESS_KEY", "minioadmin")
OBJECT_STORAGE_SECRET_KEY: str = os.getenv("OBJECT_STORAGE_SECRET_KEY", "minioadmin")
OBJECT_STORAGE_BUCKET: str = os.getenv("OBJECT_STORAGE_BUCKET", "saas-chat-agent")
LOCAL_OBJECT_STORAGE_ROOT: str = os.getenv(
    "LOCAL_OBJECT_STORAGE_ROOT", str(BASE_DIR / "local_object_storage")
)

# ---------- 向量数据库（Milvus） ----------
VECTOR_DB_HOST: str = os.getenv("VECTOR_DB_HOST", "127.0.0.1")
VECTOR_DB_PORT: int = int(os.getenv("VECTOR_DB_PORT", "19530"))
VECTOR_DB_URL: str = os.getenv(
    "VECTOR_DB_URL", f"http://{VECTOR_DB_HOST}:{VECTOR_DB_PORT}"
)
VECTOR_DB_TOKEN: str = os.getenv("VECTOR_DB_TOKEN", "")

# ---------- 离线流水线参数 ----------
INGEST_CHUNK_SIZE: int = int(os.getenv("INGEST_CHUNK_SIZE", "800"))
INGEST_CHUNK_OVERLAP: int = int(os.getenv("INGEST_CHUNK_OVERLAP", "100"))
INGEST_EMBED_BATCH_SIZE: int = int(os.getenv("INGEST_EMBED_BATCH_SIZE", "16"))

# ---------- 在线检索参数 ----------
RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))

# ---------- 内部服务通信 ----------
INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "dev-internal-secret")
