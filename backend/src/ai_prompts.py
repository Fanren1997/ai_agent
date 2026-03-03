"""Prompt rule set for mapping user text to intents/actions."""
from __future__ import annotations

import re

# 简单正则匹配的提示词规则
PROMPT_RULES = [
    {
        "intent": "greeting",
        "patterns": [r"你好", r"hi", r"hello", r"在吗", r"hey"],
        "reply": "你好👋 我是 Access Agent，可以帮你查项目、参数、数据库状态等。",
    },
    {
        "intent": "help",
        "patterns": [r"帮助", r"你能干啥", r"说明", r"支持什么", r"怎么用", r"功能"],
        "reply": (
            "📋 我支持以下操作：<br>"
            "1️⃣ 查 12NC：如“查 P0048614 的 12NC”<br>"
            "2️⃣ 查参数值：如“12NC 929003345801 的 Lumen 参数”<br>"
            "3️⃣ 查同步状态：如“现在同步到哪张表？”<br>"
            "4️⃣ 触发同步：如“刷新/同步数据库”<br>"
            "5️⃣ 导出表格：如“导出 P0048614 的 12NC/10NC/brand Excel”"
        ),
    },
    {"intent": "project_query", "patterns": [r"P\d{6,8}"], "action": "query_project_12nc"},
    {"intent": "param_query", "patterns": [r"\d{10,15}.*[a-zA-Z_]+"], "action": "query_nc_field"},
    {"intent": "sync_control", "patterns": [r"同步", r"导入", r"更新数据"], "action": "trigger_sync"},
    {
        "intent": "sync_status",
        "patterns": [r"同步状态", r"同步到哪", r"同步进度", r"现在同步到哪里"],
        "action": "get_sync_status",
    },
    {
        "intent": "export",
        "patterns": [r"导出", r"下载", r"excel", r"表格", r"export"],
        "action": "export",
    },
]


def match_prompt(user_input: str):
    """Match user input against prompt rules, return dict with intent/action/reply."""
    text = user_input  # 保留大小写，按原文匹配
    for rule in PROMPT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text):
                return {"intent": rule["intent"], "action": rule.get("action"), "reply": rule.get("reply")}
    return {"intent": "unknown", "action": None, "reply": None}
