"""
AI 服务模块：结合提示词库与数据库查询，基于上下文生成结果，并支持导出。
"""
from __future__ import annotations

import json
import re
import difflib
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

import pandas as pd
import pymysql
import requests

from src.config import LLM_CONFIG, MYSQL_CONFIG
from src.database import execute_sql, ensure_safe_select
from src.ai_prompts import match_prompt
from src.services.export_store import save_file
from src.services.chat_store import upsert_user_profile
from src.services.sync_service import get_status as get_sync_status, start_sync

# 加载 schema 信息，供 LLM 提示使用
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "src" / "schema_dump.json"
try:
    if SCHEMA_PATH.exists():
        SCHEMA_DATA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        print(f"[OK] 已加载 schema 字段文件: {SCHEMA_PATH}")
    else:
        SCHEMA_DATA = {}
        print(f"[WARN] 未找到 schema_dump 文件: {SCHEMA_PATH}")
except Exception as exc:
    SCHEMA_DATA = {}
    print(f"[ERROR] 解析 schema_dump 失败: {exc}")

# 预加载列名，便于自动匹配未知字段
SCHEMA_COLUMNS: Set[str] = set()
FIELD_ALIAS_CACHE: Dict[str, str] = {}
try:
    for cols in SCHEMA_DATA.values():
        for col in cols:
            name = col.get("name")
            if name:
                SCHEMA_COLUMNS.add(name)
except Exception:
    pass


def _norm_field_key(name: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "", name).lower()


def _auto_resolve_field(field: str) -> Optional[str]:
    """尝试基于 schema 列名自动匹配用户字段（含缓存）。"""
    if not field:
        return None
    key = _norm_field_key(field)
    if key in FIELD_ALIAS_CACHE:
        return FIELD_ALIAS_CACHE[key]

    # 直接命中
    for col in SCHEMA_COLUMNS:
        if _norm_field_key(col) == key:
            FIELD_ALIAS_CACHE[key] = col.lower()
            return FIELD_ALIAS_CACHE[key]

    # 子串匹配
    candidates = []
    for col in SCHEMA_COLUMNS:
        norm_col = _norm_field_key(col)
        if not norm_col:
            continue
        if key and (key in norm_col or norm_col in key):
            candidates.append(col)
    # 相似度匹配
    if not candidates:
        candidates = difflib.get_close_matches(field, list(SCHEMA_COLUMNS), n=3, cutoff=0.6)

    resolved = candidates[0].lower() if candidates else None
    FIELD_ALIAS_CACHE[key] = resolved or ""
    return resolved


def is_greeting(text: str) -> bool:
    greetings = ["你好", "hi", "hello", "thanks", "谢谢", "help", "帮助", "在吗"]
    lowered = text.lower()
    return any(word in lowered for word in greetings)


def extract_keywords(text: str) -> Tuple[List[str], List[str], Optional[str]]:
    projects = re.findall(r"P\d{6,8}", text, flags=re.IGNORECASE)
    projects = [p.upper() for p in projects]
    nc_codes = re.findall(r"\d{10,15}", text)
    field_match = re.findall(r"[a-zA-Z_]+", text)
    field = field_match[-1].lower() if field_match else None
    return projects, nc_codes, field


def _format_table_result(rows: List[Dict[str, Any]], max_display: int = 5) -> str:
    if not rows:
        return "没有找到相关记录。"
    num_rows = len(rows)
    display_rows = rows[:max_display]
    headers = list(display_rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "|" + "|".join([" --- " for _ in headers]) + "|"
    table_lines = [header_line, sep_line]
    for row in display_rows:
        row_vals = []
        for h in headers:
            val = row.get(h, "")
            cell = "" if val is None else str(val)
            cell = cell.replace("|", "\\|").replace("\n", " ")
            row_vals.append(cell)
        table_lines.append("| " + " | ".join(row_vals) + " |")
    table_text = "\n".join(table_lines)
    if num_rows > max_display:
        return f"📊 共找到 {num_rows} 条记录，显示前 {max_display} 条：\n\n{table_text}\n\n...（更多记录未显示）"
    return f"📊 共找到 {num_rows} 条记录：\n\n{table_text}"


def _prepare_history_messages(history: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, str]]:
    usable: List[Dict[str, str]] = []
    for msg in history[-limit:]:
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and content:
            usable.append({"role": role, "content": content})
    return usable


def _extract_field_requests(text: str) -> List[str]:
    """从文本中提取字段需求，返回标准字段名列表（去重）。"""
    lowered = text.lower()
    raw_text = text
    fields: List[str] = []

    def add(name: str):
        if name not in fields:
            fields.append(name)

    # 直接关键词
    for kw in ["power", "lifetime", "length", "weight", "height", "brand", "10nc", "ip"]:
        if kw in lowered:
            add(kw)
    # 防水/IP 等级（中文与 IPxx 形式）
    if any(kw in raw_text for kw in ["防水", "防护等级", "防水等级"]):
        add("ip")
    if re.search(r"\bip\s*\d{2}\b", raw_text, flags=re.IGNORECASE) or re.search(
        r"\bip\b", raw_text, flags=re.IGNORECASE
    ):
        add("ip")

    # 同义词映射
    if "wattage" in lowered or "lamp wattage" in lowered or "w claim" in lowered:
        add("power")
    if "life time" in lowered or "lifetime" in lowered:
        add("lifetime")

    return fields


def _extract_ip_targets(text: str) -> List[str]:
    """提取用户输入中出现的 IP 等级（如 IP44/IP65）。"""
    targets: List[str] = []
    for match in re.findall(r"ip\s*([0-9]{2})", text, flags=re.IGNORECASE):
        ip_val = f"IP{match}"
        if ip_val not in targets:
            targets.append(ip_val)
    return targets


def _extract_power_threshold(text: str) -> Optional[float]:
    """Extract a wattage threshold like "25w above" or "> 25w" from text."""
    if not text:
        return None
    patterns = [
        r"(\d+(?:\.\d+)?)\s*w\s*\u4ee5\u4e0a",
        r">\s*(\d+(?:\.\d+)?)\s*w",
    ]
    for pat in patterns:
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None

def _text_has_tl(text: str) -> bool:
    if not text:
        return False
    return re.search(r"(?i)(^|[^a-z])tl([^a-z]|$)", text) is not None


def _parse_numeric_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    matches = re.findall(r"\d+(?:\.\d+)?", str(value))
    if not matches:
        return None
    try:
        return max(float(m) for m in matches)
    except ValueError:
        return None


def _infer_field_from_history(history: List[Dict[str, Any]]) -> Optional[str]:
    """从最近的用户消息里推测字段关键词，便于无字段时沿用上下文。"""
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        content = msg.get("content") or ""
        fields = _extract_field_requests(content)
        if fields:
            return fields[0]
    return None


def _infer_projects_from_history(history: List[Dict[str, Any]]) -> List[str]:
    """从最近的用户消息里推测项目编号。"""
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        content = msg.get("content") or ""
        projects = re.findall(r"P\d{6,8}", content, flags=re.IGNORECASE)
        if projects:
            return [p.upper() for p in projects]
    return []


def _format_sync_status(status: Dict[str, Any]) -> str:
    lines = [f"同步状态: {status.get('status') or 'unknown'}"]
    if status.get("running"):
        lines.append("运行中: 是")
    if status.get("pid"):
        lines.append(f"进程 PID: {status['pid']}")
    if status.get("started_at"):
        lines.append(f"开始时间: {status['started_at']}")
    if status.get("ended_at"):
        lines.append(f"结束时间: {status['ended_at']}")
    if status.get("exit_code") is not None:
        lines.append(f"退出码: {status['exit_code']}")
    if status.get("error"):
        lines.append(f"错误信息: {status['error']}")
    output = status.get("output") or []
    if output:
        lines.append("最近输出:")
        lines.extend(output[-10:])
    return "\n".join(lines)


def _query_12nc_to_10nc(nc_codes: List[str]) -> str:
    mapping: Dict[str, List[str]] = {}
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]
        target_tables = []
        for table in all_tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0].lower() for col in cursor.fetchall()]
                if any("12nc" in c for c in cols) and any("10nc" in c for c in cols):
                    target_tables.append(table)
            except Exception:
                continue

        if not target_tables:
            return "⚠️ 未找到同时包含 12NC 和 10NC 的表，无法映射。"

        placeholders = ",".join(["%s"] * len(nc_codes))
        for table in target_tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                col_defs = [col[0] for col in cursor.fetchall()]
                col_12 = next((c for c in col_defs if "12nc" in c.lower()), None)
                col_10 = next((c for c in col_defs if "10nc" in c.lower()), None)
                if not col_12 or not col_10:
                    continue
                cursor.execute(
                    f"SELECT `{col_12}`, `{col_10}` FROM `{table}` WHERE `{col_12}` IN ({placeholders})",
                    tuple(nc_codes),
                )
                rows = cursor.fetchall()
                for row in rows:
                    nc_val = str(row[0])
                    ten_val = str(row[1])
                    mapping.setdefault(nc_val, []).append(ten_val)
            except Exception:
                continue
    except Exception as exc:
        return f"⚠️ 查询 12NC 对应 10NC 失败: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not mapping:
        return f"未找到这些 12NC 的 10NC：{nc_codes}"

    lines = ["**📊 12NC -> 10NC 对应：**"]
    for code in sorted(mapping.keys()):
        values = sorted(set(mapping[code]))
        lines.append(f"{code} -> {', '.join(values)}")
    return "\n".join(lines)


def _query_project_12nc(projects: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """查询项目编号对应的 12NC 列表，返回文本和原始行列表。"""
    result_rows: List[Dict[str, Any]] = []
    seen = set()
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]
        target_tables = [t for t in all_tables if "12nc_based" in t.lower()]
        placeholders = ",".join(["%s"] * len(projects))
        for table in target_tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0].lower() for col in cursor.fetchall()]
                if "project_code" not in cols or "12nc" not in cols:
                    continue
                cursor.execute(
                    f"SELECT Project_Code, `12NC` FROM `{table}` WHERE Project_Code IN ({placeholders})",
                    tuple(projects),
                )
                rows = cursor.fetchall()
                for row in rows:
                    key = (row[0], row[1])
                    if key in seen:
                        continue
                    seen.add(key)
                    result_rows.append({"Project_Code": row[0], "12NC": row[1]})
            except Exception:
                continue
    except Exception as exc:
        return f"⚠️ SQL 执行异常: {exc}", []
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

    if not result_rows:
        return f"未找到项目 {projects} 的任何记录。", []

    project_map: Dict[str, List[str]] = {}
    for row in result_rows:
        code = row.get("Project_Code") or row.get("project_code")
        nc_val = row.get("12NC") or row.get("12nc")
        if code:
            project_map.setdefault(code, []).append(str(nc_val))

    output_lines = ["**📊 查询结果如下：**"]
    for code, nc_list in project_map.items():
        uniques = sorted(set(nc_list))
        count = len(uniques)
        all_values = "，".join(uniques)
        output_lines.append(f"🧩 **{code}** 含有 {count} 个 12NC：{all_values}")
        output_lines.append(f"共计 {len(project_map)} 个项目（已去重合并所有表）。")
    return "\n".join(output_lines), result_rows


def _normalize_ip_value(value: Any) -> str:
    """标准化 IP 等级字符串，例如 IP 65 -> IP65。"""
    if value is None:
        return ""
    val = str(value).strip()
    if not val:
        return ""
    normalized = re.sub(r"[^0-9A-Za-z]", "", val).upper()
    if normalized.startswith("IP"):
        return normalized
    if re.fullmatch(r"\d{2}", normalized):
        return f"IP{normalized}"
    return normalized


def _extract_ip_values_from_text(value: Any) -> List[str]:
    if value is None:
        return []
    text = str(value)
    matches = re.findall(r"ip\s*([0-9]{2})", text, flags=re.IGNORECASE)
    values: List[str] = []
    for match in matches:
        ip_val = f"IP{match}"
        if ip_val not in values:
            values.append(ip_val)
    if not values:
        normalized = _normalize_ip_value(text)
        if normalized.startswith("IP") and len(normalized) == 4 and normalized[2:].isdigit():
            values.append(normalized)
    return values


def _query_project_ip_rating(projects: List[str], ip_targets: Optional[List[str]] = None) -> str:
    """统计项目下各 IP 等级数量，可选仅关注指定 IP 等级。"""
    preferred_ip_cols = [
        "camera_waterproof_ip",
        "waterproof_ip",
        "ip_rating",
        "ip_rate",
        "ip_class",
        "degree_of_protection_ip_",
        "ip",
    ]
    target_set: Set[str] = set(_normalize_ip_value(t) for t in (ip_targets or []) if _normalize_ip_value(t))
    counts: Dict[str, Dict[str, Set[str]]] = {}
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                if "project_code" not in cols_lower:
                    continue
                ip_col = None
                for pref in preferred_ip_cols:
                    if pref in cols_lower:
                        ip_col = cols[cols_lower.index(pref)]
                        break
                if not ip_col:
                    continue
                project_col = cols[cols_lower.index("project_code")]
                nc_col = None
                if any("12nc" in c for c in cols_lower):
                    nc_col = cols[cols_lower.index(next(c for c in cols_lower if "12nc" in c))]
                elif any("10nc" in c for c in cols_lower):
                    nc_col = cols[cols_lower.index(next(c for c in cols_lower if "10nc" in c))]

                placeholders = ",".join(["%s"] * len(projects))
                select_cols = [project_col, ip_col] + ([nc_col] if nc_col else [])
                cursor.execute(
                    f"SELECT {', '.join(f'`{c}`' for c in select_cols)} FROM `{table}` WHERE `{project_col}` IN ({placeholders})",
                    tuple(projects),
                )
                rows = cursor.fetchall()
                for row in rows:
                    proj_val = str(row[0]) if row[0] is not None else ""
                    ip_raw = row[1]
                    nc_val = row[2] if nc_col and len(row) > 2 else None
                    ip_norm = _normalize_ip_value(ip_raw)
                    if not ip_norm:
                        continue
                    if target_set and ip_norm not in target_set:
                        continue
                    nc_key = (
                        str(nc_val)
                        if nc_val is not None
                        else f"{proj_val or 'UNKNOWN'}-{table}-{ip_norm}"
                    )
                    counts.setdefault(proj_val, {}).setdefault(ip_norm, set()).add(nc_key)
            except Exception:
                continue
    except Exception as exc:
        return f"⚠️ 查询项目防水/IP 等级失败: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not counts:
        return f"未找到项目 {', '.join(projects)} 的防水/IP 等级数据。"

    lines: List[str] = ["项目防水/IP 等级统计："]
    for proj in projects:
        ip_map = counts.get(proj)
        if not ip_map:
            lines.append(f"- 项目 {proj}: 未查询到防水/IP 等级")
            continue
        lines.append(f"- 项目 {proj}:")
        order: List[str] = []
        seen: Set[str] = set()
        for ip in ip_targets or []:
            ip_norm = _normalize_ip_value(ip)
            if ip_norm and ip_norm in ip_map and ip_norm not in seen:
                order.append(ip_norm)
                seen.add(ip_norm)
        for ip in sorted(ip_map.keys()):
            if ip not in seen:
                order.append(ip)
                seen.add(ip)
        for ip in order:
            codes = sorted(ip_map[ip])
            sample = ", ".join(codes[:5])
            tail = " ..." if len(codes) > 5 else ""
            lines.append(f"  · {ip}: {len(codes)} 个" + (f"（示例12NC：{sample}{tail}）" if codes else ""))
    return "\n".join(lines)


def _query_12nc_ip_counts(ip_targets: Optional[List[str]] = None) -> str:
    preferred_ip_cols = [
        "camera_waterproof_ip",
        "waterproof_ip",
        "ip_rating",
        "ip_rate",
        "ip_class",
        "ip_grade",
        "degree_of_protection_ip_",
        "ip",
    ]
    target_set: Set[str] = set(_normalize_ip_value(t) for t in (ip_targets or []) if _normalize_ip_value(t))
    counts: Dict[str, Set[str]] = {}
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                if not any("12nc" in c for c in cols_lower):
                    continue
                ip_col = None
                for pref in preferred_ip_cols:
                    if pref in cols_lower:
                        ip_col = cols[cols_lower.index(pref)]
                        break
                if not ip_col:
                    continue
                key_col = cols[cols_lower.index(next(c for c in cols_lower if "12nc" in c))]
                where_clauses = [f"`{ip_col}` IS NOT NULL", f"`{ip_col}` <> ''"]
                params: List[Any] = []
                if target_set:
                    like_clauses = []
                    for ip in target_set:
                        digits = ip.replace("IP", "")
                        like_clauses.append(f"`{ip_col}` LIKE %s")
                        params.append(f"%{ip}%")
                        like_clauses.append(f"`{ip_col}` LIKE %s")
                        params.append(f"%{digits}%")
                    where_clauses.append("(" + " OR ".join(like_clauses) + ")")
                where_sql = " AND ".join(where_clauses)
                cursor.execute(
                    f"SELECT `{key_col}`, `{ip_col}` FROM `{table}` WHERE {where_sql}",
                    tuple(params),
                )
                rows = cursor.fetchall()
                for row in rows:
                    code_val = row[0]
                    ip_val = row[1]
                    if code_val is None or str(code_val).strip() == "":
                        continue
                    for ip in _extract_ip_values_from_text(ip_val):
                        if target_set and ip not in target_set:
                            continue
                        counts.setdefault(ip, set()).add(str(code_val))
            except Exception:
                continue
    except Exception as exc:
        return f"Query 12NC IP counts failed: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not counts:
        if target_set:
            return f"No 12NC IP data found for: {', '.join(sorted(target_set))}."
        return "No 12NC IP data found."

    order: List[str] = []
    for ip in ip_targets or []:
        ip_norm = _normalize_ip_value(ip)
        if ip_norm and ip_norm not in order:
            order.append(ip_norm)
    for ip in sorted(counts.keys()):
        if ip not in order:
            order.append(ip)

    lines = ["12NC IP counts:"]
    for ip in order:
        lines.append(f"- {ip}: {len(counts.get(ip, set()))}")
    return "\n".join(lines)


def _query_tl_power_over(threshold_w: float) -> str:
    tl_codes: Set[str] = set()
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM `12nc_based_part1`")
        cols = [col[0] for col in cursor.fetchall()]
        cols_lower = [c.lower() for c in cols]
        if "12nc" in cols_lower and "product_category" in cols_lower:
            col_12 = cols[cols_lower.index("12nc")]
            col_cat = cols[cols_lower.index("product_category")]
            cursor.execute(
                f"SELECT `{col_12}`, `{col_cat}` FROM `12nc_based_part1` WHERE `{col_cat}` IS NOT NULL AND `{col_cat}` <> ''"
            )
            rows = cursor.fetchall()
            for row in rows:
                code_val = row[0]
                cat_val = row[1]
                if code_val is None or cat_val is None:
                    continue
                if "TL" in str(cat_val).upper():
                    tl_codes.add(str(code_val))
    except Exception:
        tl_codes = set()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not tl_codes:
        return "No TL category data found in 12nc_based_part1."

    power_cols = [
        "lamp_wattage_(w)_claim",
        "lamp_wattage__w__claim",
        "eprel_lamp_wattage__w__claim",
        "output_power",
        "driver_maximum_output_power__w_",
    ]
    matched: Dict[str, float] = {}
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                if not any("12nc" in c for c in cols_lower):
                    continue
                key_col = cols[cols_lower.index(next(c for c in cols_lower if "12nc" in c))]
                target_cols: List[str] = []
                for pref in power_cols:
                    if pref in cols_lower:
                        target_cols.append(cols[cols_lower.index(pref)])
                if not target_cols:
                    continue
                where_parts = [f"`{c}` IS NOT NULL AND `{c}` <> ''" for c in target_cols]
                where_sql = " OR ".join(where_parts)
                select_cols = ", ".join([f"`{key_col}`"] + [f"`{c}`" for c in target_cols])
                cursor.execute(f"SELECT {select_cols} FROM `{table}` WHERE {where_sql}")
                rows = cursor.fetchall()
                for row in rows:
                    code_val = row[0]
                    if code_val is None:
                        continue
                    code_str = str(code_val)
                    if code_str not in tl_codes:
                        continue
                    for idx, col in enumerate(target_cols, start=1):
                        val = row[idx]
                        num_val = _parse_numeric_value(val)
                        if num_val is None:
                            continue
                        if num_val > threshold_w:
                            prev = matched.get(code_str)
                            if prev is None or num_val > prev:
                                matched[code_str] = num_val
            except Exception:
                continue
    except Exception as exc:
        return f"Query TL power over {threshold_w}W failed: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not matched:
        return f"No TL 12NC found with power > {threshold_w}W."

    codes = sorted(matched.keys())
    max_list = 50
    lines = [f"TL 12NC with power > {threshold_w}W: {len(codes)}"]
    for code in codes[:max_list]:
        lines.append(f"- {code} ({matched[code]}W)")
    if len(codes) > max_list:
        lines.append(f"... and {len(codes) - max_list} more.")
    return "\n".join(lines)


def _query_length(nc_codes: List[str], field: str) -> str:
    preferred_cols = ["length12nc", "lengthproject", "bcp_length", "im_length", "cas_length"]
    results = []
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                if not any("12nc" in c for c in cols_lower) and not any("10nc" in c for c in cols_lower):
                    continue
                target_col = None
                for pref in preferred_cols:
                    if pref in cols_lower:
                        target_col = cols[cols_lower.index(pref)]
                        break
                if not target_col:
                    matches = [cols[i] for i, c in enumerate(cols_lower) if "length" in c]
                    target_col = matches[0] if matches else None
                if not target_col:
                    continue
                key_col = None
                if any("12nc" in c for c in cols_lower):
                    key_col = cols[cols_lower.index(next(c for c in cols_lower if "12nc" in c))]
                elif any("10nc" in c for c in cols_lower):
                    key_col = cols[cols_lower.index(next(c for c in cols_lower if "10nc" in c))]
                else:
                    continue
                placeholders = ",".join(["%s"] * len(nc_codes))
                cursor.execute(
                    f"SELECT `{key_col}`, `{target_col}` FROM `{table}` WHERE `{key_col}` IN ({placeholders})",
                    tuple(nc_codes),
                )
                rows = cursor.fetchall()
                if rows:
                    for row in rows:
                        results.append({"code": row[0], "value": row[1], "table": table, "col": target_col})
            except Exception:
                continue
    except Exception as exc:
        return f"⚠️ 查询 length 失败: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not results:
        return f"未找到这些编号的 length 信息：{nc_codes}"

    lines = ["**📊 长度（length）查询结果：**"]
    for item in results:
        col_name = item.get("col") or "length"
        lines.append(f"{item['code']} -> {item.get('value', '')} （表 {item['table']}，列 {col_name}）")
    return "\n".join(lines)


def _query_field(nc_codes: List[str], field: str) -> str:
    """按 12NC/10NC 查询任意字段，支持同义词优先匹配，再模糊匹配，返回所有命中的列。"""
    field_lower = field.lower()
    # 自动学习：尝试根据 schema 自动映射字段
    resolved = _auto_resolve_field(field_lower)
    if resolved:
        field_lower = resolved
    priority_map = {
        "power": [
            "lamp_wattage_(w)_claim",
            "lamp_wattage__w__claim",
            "eprel_lamp_wattage__w__claim",
            "output_power",
            "driver_maximum_output_power__w_",
        ],
        "lifetime": [
            "life_time_(hours)",
            "lifetime_in_years",
            "rated_lifetime__years_",
            "lamp_lumen_maintenance_factor_at_end_of_nominal_lifetime_=70__",
        ],
        "ip": [
            "camera_waterproof_ip",
            "waterproof_ip",
            "ip_rating",
            "ip_rate",
            "ip_class",
            "degree_of_protection_ip_",
            "ip_grade",
            "ip",
        ],
    }
    collected: Dict[str, List[Dict[str, Any]]] = {}
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                key_col = None
                if any("12nc" in c for c in cols_lower):
                    key_col = cols[cols_lower.index(next(c for c in cols_lower if "12nc" in c))]
                elif any("10nc" in c for c in cols_lower):
                    key_col = cols[cols_lower.index(next(c for c in cols_lower if "10nc" in c))]
                else:
                    continue

                # 找出匹配的目标列
                target_cols: List[str] = []
                # 如果有优先列配置，则仅按优先列命中；无命中则跳过（视为未找到）
                if field_lower in priority_map:
                    for want in priority_map[field_lower]:
                        if want in cols_lower:
                            colname = cols[cols_lower.index(want)]
                            if colname not in target_cols:
                                target_cols.append(colname)
                    if not target_cols:
                        # 本表未命中优先列，跳过；最终若所有表都未命中会返回未找到
                        continue
                else:
                    # 普通字段：精确+模糊
                    if field_lower in cols_lower:
                        colname = cols[cols_lower.index(field_lower)]
                        if colname not in target_cols:
                            target_cols.append(colname)
                    fuzzy_matches = [cols[i] for i, c in enumerate(cols_lower) if field_lower in c]
                    for fm in fuzzy_matches:
                        if fm not in target_cols:
                            target_cols.append(fm)
                    if not target_cols:
                        continue

                placeholders = ",".join(["%s"] * len(nc_codes))
                for target_col in target_cols:
                    cursor.execute(
                        f"SELECT `{key_col}`, `{target_col}` FROM `{table}` WHERE `{key_col}` IN ({placeholders})",
                        tuple(nc_codes),
                    )
                    rows = cursor.fetchall()
                    if rows:
                        for row in rows:
                            code_val = row[0]
                            field_val = row[1]
                            if field_val is None or str(field_val).strip() == "":
                                continue
                            collected.setdefault(str(code_val), []).append(
                                {"value": field_val, "table": table, "col": target_col}
                            )
            except Exception:
                continue
    except Exception as exc:
        return f"数据库查询失败: {exc}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not collected:
        return f"未找到编号 {nc_codes} 的 {field} 信息。"

    output_lines = [f"**📊 查询 {field} 结果：**"]
    for code in sorted(collected.keys()):
        items = collected[code]
        seen = set()
        parts = []
        for item in items:
            key = (item["table"], item["col"], str(item["value"]))
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"{item['value']}（表 {item['table']}，列 {item['col']}）")
        output_lines.append(f"- {code} = " + "；".join(parts))
    return "\n".join(output_lines)


def _query_fields_bundle(nc_codes: List[str], fields: List[str]) -> str:
    """依次查询多个字段并汇总返回，即使未找到也标明字段名。"""
    parts = []
    for f in fields:
        if f == "length":
            result = _query_length(nc_codes, f)
        else:
            result = _query_field(nc_codes, f)
        parts.append(f"【{f}】\n{result}")
    return "\n\n".join(parts)


def _export_project_details(projects: List[str]) -> Dict[str, Any]:
    """查询项目的 12NC/10NC/Brand 并导出 Excel，返回 {message, downloadUrl}。"""
    rows: List[Dict[str, Any]] = []
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        tables = ["12nc_based_part1", "12nc_based2_part1"]
        placeholders = ",".join(["%s"] * len(projects))
        for table in tables:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [col[0] for col in cursor.fetchall()]
                cols_lower = [c.lower() for c in cols]
                if "project_code" not in cols_lower:
                    continue
                col_project = cols[cols_lower.index("project_code")]
                col_12 = next((cols[i] for i, c in enumerate(cols_lower) if "12nc" in c), None)
                col_10 = next((cols[i] for i, c in enumerate(cols_lower) if "10nc" in c), None)
                col_brand = next((cols[i] for i, c in enumerate(cols_lower) if "brand" in c), None)
                select_cols = [col_project]
                if col_12:
                    select_cols.append(col_12)
                if col_10:
                    select_cols.append(col_10)
                if col_brand:
                    select_cols.append(col_brand)
                if len(select_cols) == 1:
                    continue
                cursor.execute(
                    f"SELECT {', '.join(f'`{c}`' for c in select_cols)} FROM `{table}` WHERE `{col_project}` IN ({placeholders})",
                    tuple(projects),
                )
                fetched = cursor.fetchall()
                for row in fetched:
                    data = dict(zip(select_cols, row))
                    rows.append(data)
            except Exception:
                continue
    except Exception as exc:
        return {"message": f"⚠️ 导出失败: {exc}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not rows:
        return {"message": f"未找到项目 {projects} 的导出数据。"}

    df = pd.DataFrame(rows)
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    token =***REDACTED***
    download_url = f"/api/download/{token}"

    message = f"✅ 导出完成，共 {len(df)} 条记录。下载链接：{download_url}"
    return {"message": message, "downloadUrl": download_url}


def _update_user_profile(user_key: Optional[str], existing_profile: str, user_message: str, assistant_reply: Any) -> None:
    if not user_key or not LLM_CONFIG.get("api_key"):
        return
    if not user_message:
        return

    reply_text = assistant_reply if isinstance(assistant_reply, str) else json.dumps(assistant_reply, ensure_ascii=False)
    system_prompt = (
        "你是用户画像助手，请根据已有画像和最新对话更新画像。\n"
        "要求：最多8条，每条以“- ”开头，聚焦用户偏好、常用缩写、问答习惯。\n"
        "如果没有新增信息，请保持原样。"
    )
    user_prompt = (
        f"已有画像：\n{existing_profile or '（空）'}\n\n"
        f"最新对话：\n用户：{user_message}\n助手：{reply_text}\n\n"
        "请输出更新后的画像："
    )

    try:
        base_url = (LLM_CONFIG.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        url = base_url + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_CONFIG.get('api_key')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_CONFIG.get("model", "gpt-3.5-turbo"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        profile_text = data["choices"][0]["message"]["content"].strip()
        if profile_text:
            if len(profile_text) > 1000:
                profile_text = profile_text[:1000]
            upsert_user_profile(user_key, profile_text)
    except Exception:
        return


def _llm_query(user_message: str, history: List[Dict[str, Any]], user_profile: str = "") -> str:
    schema_lines = []
    seen_tables = set()
    for key, cols in SCHEMA_DATA.items():
        table_name = key.split("_part")[0] if "_part" in key else key
        if table_name in seen_tables:
            continue
        seen_tables.add(table_name)
        col_names = [col.get("name") for col in cols if "name" in col]
        schema_lines.append(f"{table_name} 字段: {', '.join(col_names)}")
    schema_info = "\n".join(schema_lines)
    system_prompt = (
        "你是数据库与业务查询助手，schema_dump 是领域提示词库。\n"
        "请严格基于下面的表名与字段名回答，优先使用明确的表名与列名。\n"
        "回答规则：\n"
        "1) 需要数据库数据时，仅输出 SQL（单条 SELECT），不要解释。\n"
        "2) 无需数据库或信息不足时，用中文直接回答或追问澄清，不输出 SQL。\n\n"
        f"{schema_info}"
    )
    if user_profile:
        system_prompt = (
            system_prompt
            + "\n\n用户画像与习惯（请尽量符合用户表达习惯与偏好）：\n"
            + user_profile
        )
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(_prepare_history_messages(history))
    messages.append({"role": "user", "content": user_message})

    try:
        base_url = (LLM_CONFIG.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        url = base_url + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_CONFIG.get('api_key')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_CONFIG.get("model", "gpt-3.5-turbo"),
            "messages": messages,
            "temperature": 0,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        llm_reply = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"⚠️ 无法生成 SQL 查询: {exc}"

    sql_match = re.search(r"```sql\s*([\s\S]+?)```", llm_reply, flags=re.IGNORECASE)
    if sql_match:
        sql_query = sql_match.group(1).strip()
    else:
        lines = [line.strip() for line in llm_reply.splitlines() if "SELECT" in line.upper()]
        sql_query = ""
        for line in lines:
            if line.upper().startswith("SELECT"):
                sql_query = line
                break
            if "SELECT" in line.upper():
                idx = line.upper().index("SELECT")
                sql_query = line[idx:]
                break

    if not sql_query:
        return llm_reply or "⚠️ 未生成有效的 SQL 查询，请重试。"
    if not sql_query.strip().lower().startswith("select"):
        return "⚠️ 仅允许执行 SELECT 查询。"

    try:
        safe_sql = ensure_safe_select(sql_query, max_limit=200)
    except ValueError as exc:
        return f"⚠️ SQL 校验失败：{exc}"

    try:
        result = execute_sql(safe_sql)
    except Exception as exc:
        return f"⚠️ SQL 执行错误: {exc}"

    result_list = result.get("result", []) if isinstance(result, dict) else (result or [])
    return _format_table_result(result_list)


def chat_with_ai(
    user_message: str,
    history: List[Dict[str, Any]] | None = None,
    user_profile: str = "",
    user_key: Optional[str] = None,
) -> Any:
    llm_available = bool(LLM_CONFIG.get("api_key"))

    history = history or []
    def _final(reply: Any) -> Any:
        if llm_available and user_key:
            try:
                _update_user_profile(user_key, user_profile or "", user_message, reply)
            except Exception:
                pass
        return reply
    def _fallback_if_empty(reply: Any) -> Any:
        if not llm_available:
            return reply
        if isinstance(reply, str) and ("未找到" in reply or "没有找到" in reply):
            return _llm_query(user_message, history, user_profile=user_profile)
        return reply

    search_scope = user_message
    lower_scope = search_scope.lower()
    requested_fields = _extract_field_requests(search_scope)
    ip_targets = _extract_ip_targets(search_scope)

    prompt_hit = match_prompt(user_message)
    if prompt_hit.get("reply"):
        return _final(prompt_hit["reply"])

    action = prompt_hit.get("action")
    projects, nc_codes, field = extract_keywords(search_scope)
    if not field:
        inferred = _infer_field_from_history(history)
        if inferred:
            field = inferred
    if not projects:
        inferred_projects = _infer_projects_from_history(history)
        if inferred_projects:
            projects = inferred_projects
    if not requested_fields and field:
        requested_fields = _extract_field_requests(field)

    # 导出
    if action == "export":
        if projects:
            return _final(_export_project_details(projects))
        return _final("请提供需要导出的项目号（如 P0046752）。")

    if action == "query_project_12nc":
        if projects and ("ip" in requested_fields or ip_targets):
            return _final(_query_project_ip_rating(projects, ip_targets))
        if projects:
            text, _ = _query_project_12nc(projects)
            return _final(text)
        return _final("未找到项目编号，请提供如 P0048614 的项目号。")

    if action == "query_nc_field":
        if not nc_codes:
            return _final("未找到 12NC/10NC 编号，请提供编号后再试。")
        multi_fields = requested_fields or [
            kw for kw in ["power", "lifetime", "length", "weight", "height", "brand", "ip"] if kw in lower_scope
        ]
        if multi_fields:
            result = _query_fields_bundle(nc_codes, multi_fields)
            return _final(_fallback_if_empty(result))
        if field and "length" in field:
            result = _query_length(nc_codes, field)
            return _final(_fallback_if_empty(result))
        if field:
            result = _query_field(nc_codes, field)
            return _final(_fallback_if_empty(result))

    if action == "trigger_sync":
        result = start_sync()
        if result.get("ok"):
            status = get_sync_status()
            return _final(f"{result.get('message', '同步任务已启动')}\n{_format_sync_status(status)}")
        if result.get("status") == "running":
            status = get_sync_status()
            return _final(f"{result.get('message', '同步任务正在运行')}\n{_format_sync_status(status)}")
        return _final(result.get("message", "同步任务启动失败"))

    if action == "get_sync_status":
        status = get_sync_status()
        return _final(_format_sync_status(status))

    power_threshold = _extract_power_threshold(search_scope)
    mentions_12nc = "12nc" in lower_scope or "12 nc" in lower_scope
    custom_parts: List[str] = []
    if mentions_12nc and ip_targets and not projects:
        custom_parts.append(_query_12nc_ip_counts(ip_targets))
    if power_threshold is not None and _text_has_tl(lower_scope):
        custom_parts.append(_query_tl_power_over(power_threshold))
    if custom_parts:
        return _final("\n\n".join(custom_parts))

    if is_greeting(user_message):
        return _final("你好，我是 Access Agent，可以帮你智能查询项目及 12NC/10NC 相关数据。")

    # 多字段查询（如 power + lifetime），直接返回，不回退项目/LLM
    if nc_codes:
        if requested_fields:
            result = _query_fields_bundle(nc_codes, requested_fields)
            return _final(_fallback_if_empty(result))

        if field:
            if "length" in field:
                result = _query_length(nc_codes, field)
                return _final(_fallback_if_empty(result))
            result = _query_field(nc_codes, field)
            return _final(_fallback_if_empty(result))

    # 项目防水/IP 等级统计
    if projects and ("ip" in requested_fields or ip_targets):
        return _final(_query_project_ip_rating(projects, ip_targets))

    # 项目编号 -> 12NC
    if projects:
        text, _ = _query_project_12nc(projects)
        return _final(text)

    # 兜底：让 LLM 生成 SQL
    if not llm_available:
        return _final("LLM API key is not configured. Please use supported query patterns or set the API key.")
    return _final(_llm_query(user_message, history, user_profile=user_profile))
