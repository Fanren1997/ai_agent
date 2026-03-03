"""
简单的会话与消息存储层（基于 MySQL）。
表结构：
- chat_sessions(id BIGINT AUTO_INCREMENT, title VARCHAR, created_at TIMESTAMP)
- chat_messages(id BIGINT AUTO_INCREMENT, session_id BIGINT, role VARCHAR, content TEXT, created_at TIMESTAMP)

会话用于区分连续对话，消息用于存储历史记录，便于前端继续对话。
"""

from __future__ import annotations

import pymysql
from datetime import datetime
from typing import List, Dict, Any

from src.config import CHAT_MYSQL_CONFIG

CREATE_SESSION_TABLE = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) DEFAULT '新对话',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARSET=utf8mb4;
"""

CREATE_MESSAGE_TABLE = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
) CHARSET=utf8mb4;
"""

CREATE_PROFILE_TABLE = """
CREATE TABLE IF NOT EXISTS chat_user_profiles (
    user_key VARCHAR(128) PRIMARY KEY,
    profile TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARSET=utf8mb4;
"""


def _get_conn():
    return pymysql.connect(
        host=CHAT_MYSQL_CONFIG["host"],
        user=CHAT_MYSQL_CONFIG["user"],
        password=CHAT_MYSQL_CONFIG["password"],
        database=CHAT_MYSQL_CONFIG["database"],
        port=int(CHAT_MYSQL_CONFIG.get("port", 3306)),
        charset=CHAT_MYSQL_CONFIG.get("charset", "utf8mb4"),
        autocommit=True,
    )


def init_tables():
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(CREATE_SESSION_TABLE)
        cur.execute(CREATE_MESSAGE_TABLE)
        cur.execute(CREATE_PROFILE_TABLE)
    conn.close()


def create_session(title: str = "新对话") -> int:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO chat_sessions (title) VALUES (%s)", (title,))
        session_id = cur.lastrowid
    conn.close()
    return session_id


def update_session_title(session_id: int, title: str):
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE chat_sessions SET title=%s WHERE id=%s", (title, session_id))
    conn.close()


def delete_session(session_id: int):
    """删除会话及其消息（外键级联）。"""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chat_sessions WHERE id=%s", (session_id,))
    conn.close()


def list_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, created_at FROM chat_sessions ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2].strftime("%Y-%m-%d %H:%M:%S")} for r in rows]


def add_message(session_id: int, role: str, content: str):
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )
    conn.close()


def get_messages(session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, role, content, created_at FROM chat_messages WHERE session_id=%s ORDER BY id ASC LIMIT %s",
            (session_id, limit),
        )
        rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "role": r[1],
            "content": r[2],
            "created_at": r[3].strftime("%Y-%m-%d %H:%M:%S"),
        }
        for r in rows
    ]


def get_user_profile(user_key: str) -> str:
    if not user_key:
        return ""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT profile FROM chat_user_profiles WHERE user_key=%s", (user_key,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""


def upsert_user_profile(user_key: str, profile: str):
    if not user_key:
        return
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_user_profiles (user_key, profile) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE profile=VALUES(profile)",
            (user_key, profile or ""),
        )
    conn.close()
