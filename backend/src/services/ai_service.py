# backend/src/services/ai_service.py  —— 覆盖
from __future__ import annotations
from typing import List, Dict, Generator
from openai import OpenAI
from src.config import Config

Message = Dict[str, str]

class AIService:
    def __init__(self) -> None:
        if not Config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY/DEEPSEEK_API_KEY 未设置，请检查 system/.env")

        # 与 DeepSeek 文档一致
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_API_BASE  # https://api.deepseek.com/v1
        )
        self.model = Config.OPENAI_MODEL   # deepseek-chat / deepseek-reasoner

    def chat(self, messages: List[Message], temperature: float = 0.2, stream: bool = False
             ) -> str | Generator[str, None, None]:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, stream=stream
        )
        if stream:
            def gen() -> Generator[str, None, None]:
                for chunk in resp:
                    delta = chunk.choices[0].delta
                    if delta and getattr(delta, "content", None):
                        yield delta.content
            return gen()
        return resp.choices[0].message.content or ""

    def nl2sql(self, schema_text: str, user_query: str) -> str:
        sys_msg = {"role": "system", "content":
            "你是SQL助手。只返回单条只读的 MySQL SELECT；禁止 DML/DDL；对表名/列名用反引号（`）。示例：SELECT * FROM `t` LIMIT 10;"}
        usr_msg = {"role": "user", "content": f"数据库结构：\n{schema_text}\n\n用户问题：{user_query}\n\n只返回SQL："}
        sql = self.chat([sys_msg, usr_msg], temperature=0)
        return (sql or "").strip()
