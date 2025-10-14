# -*- coding: utf-8 -*-
"""
系统配置模块 · Access Agent
从环境变量加载 DeepSeek / MySQL 配置信息
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# ===== 加载 .env =====
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"✅ 已加载配置文件: {ENV_PATH}")
else:
    print("⚠️ 未找到 .env 文件，使用系统环境变量。")


# ===== LLM / AI 模型配置 =====
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("DEEPSEEK_API_BASE") or os.getenv("OPENAI_API_BASE"),
    "model": os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL"),
}

# ===== MySQL 配置 =====
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "access_user"),
    "password": os.getenv("MYSQL_PASSWORD", "your_password"),
    "database": os.getenv("MYSQL_DATABASE", "access_migration_db"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}

# ===== 检查 =====
if not MYSQL_CONFIG["password"] or MYSQL_CONFIG["password"] == "your_password":
    print("⚠️ MySQL 密码尚未配置，请检查 .env 文件。")

if not LLM_CONFIG["api_key"]:
    print("⚠️ 未检测到 LLM API KEY，请检查 .env 文件。")
