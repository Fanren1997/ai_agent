# system/ping_deepseek.py
from pathlib import Path
from dotenv import load_dotenv
import os
from openai import OpenAI

# 直接加载 system/.env
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

api_key = os.getenv("OPENAI_API_KEY")
base    = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
assert api_key, "OPENAI_API_KEY 未设置"

client = OpenAI(api_key=api_key, base_url=base)
resp = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用一句话自我介绍"},
    ],
    stream=False
)
print("OK:", resp.choices[0].message.content[:80])
