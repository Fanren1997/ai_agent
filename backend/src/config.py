"""Config loader: read DeepSeek / MySQL settings from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"[OK] 已加载配置文件: {ENV_PATH}")
else:
    print("[WARN] 未找到 .env 文件，使用系统环境变量")

# LLM / AI 模型配置
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("DEEPSEEK_API_BASE") or os.getenv("OPENAI_API_BASE"),
    "model": os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL"),
}

# MySQL 配置
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "access_user"),
    "password": os.getenv("MYSQL_PASSWORD", "your_password"),
    "database": os.getenv("MYSQL_DATABASE", "access_migration_db"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}

# Chat å­˜æ”¾ç‹¬ç«‹ MySQL é…ç½®ï¼Œé»˜è®¤é‡‡ç”¨ä¸Žä¸»æ•°æ®ä¸åŒçš„æ•°æ®åº“å
CHAT_MYSQL_CONFIG = {
    "host": os.getenv("CHAT_MYSQL_HOST", MYSQL_CONFIG["host"]),
    "user": os.getenv("CHAT_MYSQL_USER", MYSQL_CONFIG["user"]),
    "password": os.getenv("CHAT_MYSQL_PASSWORD", MYSQL_CONFIG["password"]),
    "database": os.getenv("CHAT_MYSQL_DATABASE", "access_chat_db"),
    "charset": os.getenv("CHAT_MYSQL_CHARSET", MYSQL_CONFIG["charset"]),
    "port": int(os.getenv("CHAT_MYSQL_PORT", str(MYSQL_CONFIG.get("port", 3306)))),
}

if not MYSQL_CONFIG["password"] or MYSQL_CONFIG["password"] == "your_password":
    print("[WARN] MySQL 密码未配置，请检查 .env")

if not LLM_CONFIG["api_key"]:
    print("[WARN] 未检测到 LLM API KEY，请检查 .env")
