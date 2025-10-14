# -*- coding: utf-8 -*-
"""
Access Agent API · 自然语言 → SQL + 数据库执行
保证所有响应为 JSON（防止前端解析错误）
"""

from flask import Blueprint, request, jsonify
import re
import traceback

# ✅ 修正后的导入路径
from src.services.ai_service import chat_with_ai
from src.database import execute_sql
from src.config import MYSQL_CONFIG, LLM_CONFIG


api_bp = Blueprint("api", __name__, url_prefix="/api")


# ============ 聊天 + SQL 查询接口 ============
@api_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_input = data.get("messages", [{}])[0].get("content", "").strip()

        if not user_input:
            return jsonify({"error": "未提供输入内容"}), 400

        print(f"🧠 用户输入: {user_input}")

        # 调用 AI 模块
        ai_reply = chat_with_ai(user_input)
        print(f"🧠 AI 输出:\n{ai_reply}")

        # 提取 SQL
        sql = extract_sql(ai_reply if isinstance(ai_reply, str) else str(ai_reply))
        if not sql:
            return jsonify({
                "message": "未检测到可执行的 SQL",
                "ai_reply": ai_reply
            }), 200

        # 仅允许 SELECT 查询
        if not sql.strip().upper().startswith("SELECT"):
            return jsonify({
                "message": "仅允许执行 SELECT 查询",
                "sql": sql
            }), 200

        print(f"🧠 执行 SQL: {sql}")

        result = execute_sql(sql)
        return jsonify({
            "message": "查询成功",
            "sql": sql,
            "result": result
        }), 200

    except Exception as e:
        print("❌ /api/chat 全局错误:", e)
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# ============ SQL 提取工具 ============
def extract_sql(text: str) -> str:
    if not text:
        return ""

    # 提取 ```sql``` 代码块
    match = re.search(r"```sql(.*?)```", text, re.S | re.I)
    if match:
        return match.group(1).strip()

    # 提取以 SELECT 开头的语句
    lines = [line.strip() for line in text.splitlines() if "SELECT" in line.upper()]
    for line in lines:
        if line.upper().startswith("SELECT"):
            return line
        if "SELECT" in line.upper():
            idx = line.upper().index("SELECT")
            return line[idx:]
    return ""


# ============ 健康检查 ============
@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "mysql": MYSQL_CONFIG,
        "llm": {
            "model": LLM_CONFIG.get("model"),
            "base_url": LLM_CONFIG.get("base_url")
        }
    })


# ============ 直接 SQL 查询接口 ============
@api_bp.route("/query", methods=["POST"])
def query():
    try:
        sql = request.get_json(force=True).get("sql", "").strip()
        if not sql:
            return jsonify({"error": "未提供 SQL 语句"}), 400

        if not sql.upper().startswith("SELECT"):
            return jsonify({"error": "仅允许 SELECT 查询"}), 400

        print(f"🧠 手动执行 SQL: {sql}")
        result = execute_sql(sql)
        return jsonify({
            "message": "执行成功",
            "result": result,
            "sql": sql
        }), 200

    except Exception as e:
        print("❌ /api/query 错误:", e)
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500
