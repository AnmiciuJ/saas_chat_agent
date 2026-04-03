from pathlib import Path

import config


def write_object(storage_key, data):
    root = Path(config.LOCAL_OBJECT_STORAGE_ROOT)
    full = root / storage_key
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)


def read_object(storage_key):
    root = Path(config.LOCAL_OBJECT_STORAGE_ROOT)
    full = root / storage_key
    return full.read_bytes()
