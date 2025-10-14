# backend/src/config.py
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
