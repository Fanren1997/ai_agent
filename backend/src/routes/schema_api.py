"""
Schema 管理 API
-------------------------------------------------
负责管理 static/schema_prompts_bilingual.json 提示词库。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request

schema_bp = Blueprint("schema_api", __name__, url_prefix="/api/schema")

# static 目录下的 schema 文件路径
SCHEMA_PATH = Path(__file__).parents[2] / "static" / "schema_prompts_bilingual.json"
_schema_lock = threading.Lock()


def _require_admin_token():
    token = os.getenv("SCHEMA_API_TOKEN")
    provided = request.headers.get("X-Admin-Token") or request.args.get("token")
    if not token:
        return False, "服务未配置 SCHEMA_API_TOKEN，默认禁止写入 schema。"
    if provided != token:
        return False, "缺少或错误的管理令牌，请在请求头 X-Admin-Token 中提供。"
    return True, ""


def _load_schema() -> Dict[str, Any]:
    """从文件加载 schema 提示词库。"""
    if not SCHEMA_PATH.exists():
        return {}

    try:
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[ERROR] 加载 schema 文件失败: {exc}")
        return {}


def _save_schema(data: Dict[str, Any]) -> None:
    """保存 schema 提示词库到文件。"""
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SCHEMA_PATH.with_suffix(".tmp.json")

    with _schema_lock:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(SCHEMA_PATH)
        print(f"[OK] 已保存 schema 提示词库: {SCHEMA_PATH}")


@schema_bp.get("/all")
def get_all_schema():
    """返回完整的 schema_prompts_bilingual.json 内容。"""
    data = _load_schema()
    return jsonify({"ok": True, "schema": data})


@schema_bp.get("/tables")
def list_tables():
    """返回所有表名列表。"""
    data = _load_schema()
    tables = sorted(list(data.keys()))
    return jsonify({"ok": True, "tables": tables})


@schema_bp.get("/table/<table_name>")
def get_table(table_name: str):
    """获取单个表的字段配置。"""
    data = _load_schema()
    table = data.get(table_name)
    if table is None:
        return jsonify({"ok": False, "error": f"表 {table_name} 不存在于 schema 提示词库中"}), 404
    return jsonify({"ok": True, "table": table_name, "columns": table})


@schema_bp.post("/table/<table_name>")
def update_table(table_name: str):
    """
    更新或创建单个表的字段配置：
    请求体应为 JSON 对象：
    {
      "ColumnA": {"zh": "...", "en": "...", "alias": [...]},
      "ColumnB": {...}
    }
    """
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"ok": False, "error": "请求体必须是 JSON 对象（字段名 -> 配置）"}), 400

    ok, err = _require_admin_token()
    if not ok:
        return jsonify({"ok": False, "error": err}), 403

    data = _load_schema()
    data[table_name] = body
    _save_schema(data)
    return jsonify({"ok": True, "msg": f"表 {table_name} 已更新", "columns_count": len(body)})


@schema_bp.post("/save_all")
def save_all_schema():
    """
    整体覆盖保存 schema 提示词库。
    请求体为完整的 JSON 对象（表名 -> 字段配置）。
    """
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"ok": False, "error": "请求体必须是 JSON 对象（表名 -> 字段配置）"}), 400

    ok, err = _require_admin_token()
    if not ok:
        return jsonify({"ok": False, "error": err}), 403

    _save_schema(body)
    return jsonify({"ok": True, "msg": "schema 提示词库已整体覆盖保存", "tables_count": len(body)})


@schema_bp.get("/ping")
def ping():
    """便捷健康检查。"""
    return jsonify({"ok": True, "msg": "schema api alive", "path": str(SCHEMA_PATH)})
