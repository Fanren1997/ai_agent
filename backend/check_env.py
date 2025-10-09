# system/backend/check_env.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 system/.env
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

for key in [
    "OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL",
    "DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE", "DEEPSEEK_MODEL",
    "MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"
]:
    val = os.getenv(key)
    print(f"{key}: {'OK' if val else 'MISSING'}")
