"""
Access Agent API · 自然语言 -> SQL + 数据库执行，保证所有响应为 JSON。
"""

from __future__ import annotations

import traceback
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from src.config import LLM_CONFIG, MYSQL_CONFIG
from src.database import execute_sql, ensure_safe_select
from src.services.ai_service import chat_with_ai
from src.services.chat_store import (
    init_tables,
    create_session,
    list_sessions,
    add_message,
    get_messages,
    get_user_profile,
    update_session_title,
    delete_session,
)
from src.services.export_store import pop_file

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/chat", methods=["POST"])
def chat():
    """聊天 + SQL 查询接口。兼容 message 与 messages，两种字段。可传 sessionId 以使用历史上下文。"""
    try:
        data = request.get_json(force=True) or {}
        session_id = data.get("sessionId")
        user_id = data.get("userId")
        user_input = (data.get("message") or (data.get("messages") or [{}])[0].get("content") or "").strip()

        if not user_input:
            return jsonify({"error": "未提供输入内容"}), 400

        print(f"[USER] {user_input}")

        history_msgs = []
        user_key = None
        if user_id:
            user_key = str(user_id)
        elif session_id:
            user_key = f"session:{session_id}"

        if session_id or user_key:
            try:
                init_tables()
            except Exception as exc:
                print(f"[WARN] 初始化聊天表失败: {exc}")

        if session_id:
            try:
                history_records = get_messages(int(session_id), limit=50)
                history_msgs = [{"role": m["role"], "content": m["content"]} for m in history_records]
            except Exception as exc:
                print(f"[WARN] 读取历史消息失败: {exc}")

        user_profile = ""
        if user_key:
            try:
                user_profile = get_user_profile(user_key)
            except Exception as exc:
                print(f"[WARN] 读取用户画像失败: {exc}")

        ai_reply = chat_with_ai(
            user_input,
            history=history_msgs,
            user_profile=user_profile,
            user_key=user_key,
        )
        print(f"[AI] {ai_reply}")

        # 会话/消息持久化（仅当提供 sessionId 时）
        try:
            if session_id:
                add_message(int(session_id), "user", user_input)
                add_message(int(session_id), "assistant", ai_reply if isinstance(ai_reply, str) else str(ai_reply))
        except Exception as exc:
            print(f"[WARN] 保存消息失败: {exc}")

        if isinstance(ai_reply, dict):
            return jsonify(ai_reply), 200
        if isinstance(ai_reply, list):
            return jsonify({"result": ai_reply}), 200
        return jsonify({"message": ai_reply}), 200

    except Exception as exc:
        print("接口 /api/chat 全局错误:", exc)
        traceback.print_exc()
        return jsonify({"error": str(exc), "trace": traceback.format_exc()}), 500


@api_bp.route("/sessions", methods=["GET"])
def sessions():
    """列出最近的会话。"""
    init_tables()
    return jsonify({"sessions": list_sessions()})


@api_bp.route("/sessions", methods=["POST"])
def sessions_create():
    """创建新会话，可传 title。"""
    init_tables()
    data = request.get_json(silent=True) or {}
    title = data.get("title") or "新对话"
    sid = create_session(title)
    return jsonify({"sessionId": sid, "title": title})


@api_bp.route("/sessions/<int:sid>", methods=["PUT"])
def sessions_update(sid: int):
    """更新会话标题。"""
    init_tables()
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title 不能为空"}), 400
    update_session_title(sid, title)
    return jsonify({"sessionId": sid, "title": title})


@api_bp.route("/sessions/<int:sid>", methods=["DELETE"])
def sessions_delete(sid: int):
    """删除会话及其历史。"""
    init_tables()
    delete_session(sid)
    return jsonify({"sessionId": sid, "deleted": True})


@api_bp.route("/sessions/<int:sid>/messages", methods=["GET"])
def session_messages(sid: int):
    """获取指定会话的历史消息。"""
    init_tables()
    msgs = get_messages(sid, limit=200)
    return jsonify({"sessionId": sid, "messages": msgs})


@api_bp.route("/health", methods=["GET"])
def health():
    """健康检查，避免泄露敏感信息。"""
    return jsonify(
        {
            "ok": True,
            "details": {
                "mysql_host": MYSQL_CONFIG.get("host"),
                "mysql_db": MYSQL_CONFIG.get("database"),
                "llm_model": LLM_CONFIG.get("model"),
                "llm_base_url": LLM_CONFIG.get("base_url"),
                "llm_configured": bool(LLM_CONFIG.get("api_key")),
            },
        }
    )


@api_bp.route("/query", methods=["POST"])
def query():
    """直接 SQL 查询接口，仅允许 SELECT。"""
    try:
        sql = (request.get_json(force=True) or {}).get("sql", "").strip()
        if not sql:
            return jsonify({"error": "未提供 SQL 语句"}), 400

        try:
            safe_sql = ensure_safe_select(sql, max_limit=200)
        except ValueError as exc:
            return jsonify({"error": f"SQL 校验失败：{exc}"}), 400

        print(f"[SQL/manual] {safe_sql}")
        result = execute_sql(safe_sql)
        return jsonify({"message": "执行成功", "result": result, "sql": sql}), 200

    except Exception as exc:
        print("接口 /api/query 错误:", exc)
        traceback.print_exc()
        return jsonify({"error": str(exc), "trace": traceback.format_exc()}), 500


@api_bp.route("/download/<token>", methods=["GET"])
def download(token: str):
    """下载导出的 Excel 文件（一次性 token）。"""
    data = pop_file(token)
    if not data:
        return jsonify({"error": "链接已失效或文件不存在"}), 404
    buf = BytesIO(data["content"])
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=data.get("filename", "export.xlsx"),
    )
