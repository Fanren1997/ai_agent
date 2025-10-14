# backend/src/routes/api.py
from flask import Blueprint, jsonify, request
from src.database import db_manager, check_db_connection
from src.services.ai_service import chat_with_ai
import json

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
def health_check():
    """系统健康检查"""
    try:
        db_ok = check_db_connection()
        tables = db_manager.get_tables()
        status = {
            "db": "ok" if db_ok else "failed",
            "tables": tables,
            "llm_base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        }
        return jsonify({"ok": db_ok, "details": status})
    except Exception as e:
        return jsonify({"ok": False, "details": {"db": f"error: {e}"}}), 500


@api_bp.route("/chat", methods=["POST"])
def chat():
    """
    智能问答接口：
    1. 根据自然语言生成 SQL
    2. 执行 SQL
    3. AI 总结结果
    """
    try:
        data = request.get_json(force=True)
        messages = data.get("messages", [])
        if not messages:
            return jsonify({"error": "Empty messages"}), 400

        user_msg = messages[-1]["content"].strip()

        # 1️⃣ 获取数据库表结构信息（让 AI 能理解你的表）
        tables = db_manager.get_tables()
        schema_hint = "当前数据库包含以下表：" + ", ".join(tables)

        # （可选）进一步获取字段名
        table_columns = {}
        try:
            for table in tables:
                columns = db_manager.execute_query(f"SHOW COLUMNS FROM {table}")
                table_columns[table] = [c["Field"] for c in columns]
        except Exception:
            pass

        schema_context = json.dumps(table_columns, ensure_ascii=False)

        # 2️⃣ 让 AI 生成 SQL
        prompt_sql = [
            {
                "role": "system",
                "content": (
                    "你是一个 MySQL 专家，根据用户问题生成正确的 SQL 查询语句。"
                    "请使用现有表结构，不要虚构表名或字段名。"
                    "仅输出 SQL，不解释。"
                )
            },
            {
                "role": "user",
                "content": f"{schema_hint}\n字段信息如下：{schema_context}\n\n用户问题：{user_msg}"
            },
        ]

        sql_text = chat_with_ai(prompt_sql)
        print(f"🧠 AI 生成的 SQL:\n{sql_text}")

        # 3️⃣ 执行 SQL 查询
        try:
            result = db_manager.execute_query(sql_text)
        except Exception as e:
            return jsonify({
                "error": f"SQL执行错误: {e}",
                "sql": sql_text
            }), 500

        # 4️⃣ AI 总结结果
        prompt_summary = [
            {"role": "system", "content": "你是一个数据分析助手，请用简洁中文总结SQL结果。"},
            {"role": "user", "content": f"SQL:\n{sql_text}\n\n结果:\n{json.dumps(result, ensure_ascii=False, indent=2)}"}
        ]
        summary = chat_with_ai(prompt_summary)

        return jsonify({
            "sql": sql_text,
            "result": result,
            "summary": summary
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
