"""Database helpers for connecting to MySQL and running queries."""

from __future__ import annotations

import re

import pandas as pd
import pymysql

from src.config import MYSQL_CONFIG


def ensure_safe_select(sql: str, max_limit: int = 200) -> str:
    """
    Basic guardrail for SELECT statements:
    - only allow single SELECT
    - forbid dangerous keywords (DML/DDL/outfile/comments)
    - enforce a LIMIT to avoid大表扫描
    """
    if not sql or not sql.strip():
        raise ValueError("SQL 不能为空")

    cleaned = sql.strip().rstrip(";")
    lowered = cleaned.lower()

    if not lowered.startswith("select"):
        raise ValueError("仅允许执行 SELECT 语句")
    if ";" in cleaned:
        raise ValueError("仅允许单条 SELECT 语句")

    forbidden_snippets = [
        " into outfile",
        " into dumpfile",
        "load data",
        " update ",
        " delete ",
        " insert ",
        " alter ",
        " drop ",
        " truncate ",
        " create ",
        " replace ",
        " rename ",
        " union ",
        "--",
        "/*",
    ]
    for snippet in forbidden_snippets:
        if snippet in lowered:
            raise ValueError(f"SQL 包含禁用片段: {snippet.strip()}")

    limit_match = re.search(r"limit\s+(\d+)", lowered, flags=re.IGNORECASE)
    if limit_match:
        try:
            limit_val = int(limit_match.group(1))
            if limit_val > max_limit:
                cleaned = re.sub(r"limit\s+\d+(\s*,\s*\d+)?", f"LIMIT {max_limit}", cleaned, flags=re.IGNORECASE)
        except ValueError:
            cleaned = re.sub(r"limit\s+[^\s]+", f"LIMIT {max_limit}", cleaned, flags=re.IGNORECASE)
    else:
        cleaned = f"{cleaned} LIMIT {max_limit}"

    return cleaned


def get_connection():
    """Get a MySQL connection object."""
    try:
        return pymysql.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=***REDACTED***
            database=MYSQL_CONFIG["database"],
            port=int(MYSQL_CONFIG.get("port", 3306)),
            charset=MYSQL_CONFIG.get("charset", "utf8mb4"),
            autocommit=True,
        )
    except Exception as exc:
        print(f"[ERROR] 数据库连接失败: {exc}")
        return None


def execute_sql(sql: str, params=None):
    """Run a SELECT statement and return rows as dicts."""
    conn = get_connection()
    if not conn:
        return {"error": "无法连接数据库"}

    try:
        print(f"[DB] 目标: {MYSQL_CONFIG['database']} @ {MYSQL_CONFIG['host']}")
        print(f"[SQL] {sql}")

        if params:
            # Use cursor when parameters are provided to avoid placeholder issues.
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]
        else:
            df = pd.read_sql(sql, conn)
            result = df.to_dict(orient="records")

        if not result:
            return {"message": "查询无结果", "result": []}

        print(f"[DB] 返回 {len(result)} 条记录")
        return result

    except Exception as exc:
        print(f"[ERROR] SQL 执行错误: {exc}")
        return {"error": f"SQL执行错误: {exc}"}

    finally:
        conn.close()


def execute_non_query(sql: str, params=None):
    """Execute INSERT/UPDATE/DDL and return affected rows."""
    conn = get_connection()
    if not conn:
        return {"error": "无法连接数据库"}
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return {"affected": cursor.rowcount}
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] SQL 执行错误: {exc}")
        return {"error": f"SQL执行错误: {exc}"}
    finally:
        conn.close()
