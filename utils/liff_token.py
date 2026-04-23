"""
LIFF session token 工具

用途：
    Bot 送出 LIFF 連結時產生一次性 token，並將 token → user_id 對應存在記憶體。
    LIFF 提交表單時帶回 token，server 以 resolve() 換回 user_id。
    這樣不需要 liff.getProfile() 的 userId 與 Messaging API 一致。
"""

import secrets
from datetime import datetime, timedelta

# { token: (user_id, expiry) }
_store: dict = {}


def create(user_id: str, ttl_minutes: int = 30) -> str:
    """產生一次性 token 並記錄對應的 user_id，有效期 ttl_minutes 分鐘"""
    token = secrets.token_urlsafe(16)
    _store[token] = (user_id, datetime.now() + timedelta(minutes=ttl_minutes))
    return token


def resolve(token: str) -> str | None:
    """
    以 token 換回 user_id（一次性使用，用後即刪）。
    token 不存在或已過期則回傳 None。
    """
    entry = _store.pop(token, None)
    if not entry:
        return None
    user_id, expiry = entry
    return user_id if datetime.now() <= expiry else None
