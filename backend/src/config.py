# backend/src/config.py  —— 覆盖/确保如下
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# 指向 system/.env（注意是 parents[2]）
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True, encoding="utf-8")

# 兜底：若关键变量仍空，再手工写入 os.environ（防止某些环境下加载失败）
if (not os.getenv("OPENAI_API_KEY")) or (not os.getenv("OPENAI_API_BASE")):
    if ENV_PATH.exists():
        for k, v in dotenv_values(ENV_PATH, encoding="utf-8").items():
            if v is not None:
                os.environ[k] = str(v)

class Config:
    # —— LLM（DeepSeek / OpenAI 兼容）——
    OPENAI_API_KEY  = os.getenv("DEEPSEEK_API_KEY")  or os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.getenv("DEEPSEEK_API_BASE") or os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    OPENAI_MODEL    = os.getenv("DEEPSEEK_MODEL")    or os.getenv("OPENAI_MODEL", "deepseek-chat")

    # —— MySQL ——（保持你的原值）
    MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER     = os.getenv("MYSQL_USER", "access_user")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "access_migration_db")

    PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))
