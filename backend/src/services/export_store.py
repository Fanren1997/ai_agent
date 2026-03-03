from __future__ import annotations

import time
import uuid
from typing import Optional, Dict, Any

EXPORT_CACHE: Dict[str, Dict[str, Any]] = {}


def save_file(content: bytes, filename: str, ttl: int = 600) -> str:
    """存储导出文件到内存缓存，返回一次性 token。"""
    token = uuid.uuid4().hex
    EXPORT_CACHE[token] = {
        "content": content,
        "filename": filename,
        "expires": time.time() + ttl,
    }
    return token


def pop_file(token: str) -> Optional[Dict[str, Any]]:
    """获取并删除缓存的文件，如果过期或不存在返回 None。"""
    data = EXPORT_CACHE.pop(token, None)
    if not data:
        return None
    if data["expires"] < time.time():
        return None
    return data
