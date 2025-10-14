# backend/src/services/ai_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# --- 自动加载 .env ---
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_API_BASE") or os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL", "deepseek-chat")

if not API_KEY:
    raise RuntimeError("❌ 环境变量 DEEPSEEK_API_KEY / OPENAI_API_KEY 未设置")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat_with_ai(messages):
    """
    输入消息数组 [{'role':'user','content':'你好'}]
    输出 AI 回复文本
    """
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=False
    )
    return resp.choices[0].message.content.strip()
