import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "dev-insecure-change-me"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

ENV_MODE = "development"

USE_SQLITE = False
DB_ENGINE = "django.db.backends.mysql"
DB_NAME = "saas_chat_agent"
DB_USER = "root"
DB_PASSWORD = "123456"
DB_HOST = "127.0.0.1"
DB_PORT = 3306

LLM_API_BASE_URL = ""
LLM_API_KEY = ""
LLM_DEFAULT_MODEL = ""

EMBEDDING_API_BASE_URL = ""
EMBEDDING_API_KEY = ""
EMBEDDING_DEFAULT_MODEL = ""

REDIS_URL = ""
CELERY_BROKER_URL = ""
CELERY_RESULT_BACKEND = ""

OBJECT_STORAGE_ENDPOINT = ""
OBJECT_STORAGE_ACCESS_KEY = ""
OBJECT_STORAGE_SECRET_KEY = ""
OBJECT_STORAGE_BUCKET = ""

LOCAL_OBJECT_STORAGE_ROOT = str(BASE_DIR / "local_object_storage")

VECTOR_DB_URL = ""
VECTOR_DB_API_KEY = ""

INGEST_CHUNK_SIZE = 800
INGEST_CHUNK_OVERLAP = 100
INGEST_EMBED_BATCH_SIZE = 16

RETRIEVAL_TOP_K = 8

INTERNAL_API_SECRET = "dev-internal-secret"

if "DJANGO_SECRET_KEY" in os.environ:
    SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
if "DJANGO_DEBUG" in os.environ:
    DEBUG = os.environ["DJANGO_DEBUG"].lower() in ("1", "true", "yes", "on")
if "DJANGO_ALLOWED_HOSTS" in os.environ:
    ALLOWED_HOSTS = [
        h.strip()
        for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
        if h.strip()
    ]
if "USE_SQLITE" in os.environ:
    USE_SQLITE = os.environ["USE_SQLITE"].lower() in ("1", "true", "yes", "on")
for _k, _v in (
    ("DB_ENGINE", DB_ENGINE),
    ("DB_NAME", DB_NAME),
    ("DB_USER", DB_USER),
    ("DB_PASSWORD", DB_PASSWORD),
    ("DB_HOST", DB_HOST),
):
    if _k in os.environ:
        globals()[_k] = os.environ[_k]
if "DB_PORT" in os.environ:
    DB_PORT = int(os.environ["DB_PORT"])
for _k in (
    "LLM_API_BASE_URL",
    "LLM_API_KEY",
    "LLM_DEFAULT_MODEL",
    "EMBEDDING_API_BASE_URL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_DEFAULT_MODEL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "OBJECT_STORAGE_ENDPOINT",
    "OBJECT_STORAGE_ACCESS_KEY",
    "OBJECT_STORAGE_SECRET_KEY",
    "OBJECT_STORAGE_BUCKET",
    "VECTOR_DB_URL",
    "VECTOR_DB_API_KEY",
    "INTERNAL_API_SECRET",
    "LOCAL_OBJECT_STORAGE_ROOT",
):
    if _k in os.environ:
        globals()[_k] = os.environ[_k]
if "INGEST_CHUNK_SIZE" in os.environ:
    INGEST_CHUNK_SIZE = int(os.environ["INGEST_CHUNK_SIZE"])
if "INGEST_CHUNK_OVERLAP" in os.environ:
    INGEST_CHUNK_OVERLAP = int(os.environ["INGEST_CHUNK_OVERLAP"])
if "INGEST_EMBED_BATCH_SIZE" in os.environ:
    INGEST_EMBED_BATCH_SIZE = int(os.environ["INGEST_EMBED_BATCH_SIZE"])
if "RETRIEVAL_TOP_K" in os.environ:
    RETRIEVAL_TOP_K = int(os.environ["RETRIEVAL_TOP_K"])
