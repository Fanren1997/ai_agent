# -*- coding: utf-8 -*-
"""
AI 服务模块（跨表智能查询 + 汇总输出）
"""

import re
import pymysql
import pandas as pd


# ===================== MySQL 配置 =====================
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "access_user",
    "password": "wvqbIcZwf5/qgm8V",
    "database": "access_migration_db",
    "charset": "utf8mb4",
}

SEARCH_TABLES = ["12NC_based2", "10NC_based", "test_result"]


# ===================== 工具函数 =====================
def get_connection():
    return pymysql.connect(**MYSQL_CONFIG)


def is_greeting(text: str) -> bool:
    greetings = ["你好", "hi", "hello", "嗨", "谢谢", "help", "帮助", "在吗"]
    return any(word in text.lower() for word in greetings)


def extract_keywords(text: str):
    """提取项目号（P开头）或12NC编号或字段"""
    projects = re.findall(r"P\d{6,8}", text, re.I)
    nc_codes = re.findall(r"\d{10,15}", text)
    field_match = re.findall(r"[a-zA-Z_]+", text)
    field = field_match[-1].lower() if field_match else None
    return projects, nc_codes, field


# ===================== 主逻辑 =====================
def chat_with_ai(user_input: str):
    if is_greeting(user_input):
        return {"message": "你好！我是 Access Agent，可以帮你智能查询项目、12NC 或参数 😊"}

    projects, nc_codes, field = extract_keywords(user_input)

    conn = get_connection()
    cursor = conn.cursor()
    output = {"message": "", "summary": [], "details": []}

    # === 如果输入包含项目号 ===
    if projects:
        try:
            sql = f"""
                SELECT Project_Code, 12NC
                FROM 12NC_based2
                WHERE Project_Code IN ({','.join(['%s'] * len(projects))})
            """
            cursor.execute(sql, tuple(projects))
            rows = cursor.fetchall()

            if not rows:
                return {"message": f"未找到项目 {projects} 的任何记录。"}

            df = pd.DataFrame(rows, columns=["Project_Code", "12NC"])

            # 汇总统计
            summary = df.groupby("Project_Code").size().reset_index(name="12NC数量")
            output["summary"] = summary.to_dict(orient="records")
            output["details"] = df.to_dict(orient="records")
            output["message"] = f"查询完成，共 {len(summary)} 个项目。"

        except Exception as e:
            output["message"] = f"SQL 执行异常: {e}"

    # === 如果输入是12NC查询（如查lumen） ===
    elif nc_codes and field:
        for table in SEARCH_TABLES:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                columns = [r[0].lower() for r in cursor.fetchall()]
                if field not in columns:
                    continue
                key_col = "12NC" if "12NC" in columns else "10NC"
                sql = f"SELECT {key_col}, `{field}` FROM `{table}` WHERE {key_col} IN ({','.join(['%s'] * len(nc_codes))})"
                cursor.execute(sql, tuple(nc_codes))
                rows = cursor.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=[key_col, field])
                    output["details"].append({
                        "table": table,
                        "count": len(df),
                        "data": df.to_dict(orient="records")
                    })
            except Exception as e:
                continue

        output["message"] = f"共在 {len(output['details'])} 张表中找到结果。"

    else:
        output["message"] = "请提供明确的查询条件，例如 12NC 或 Project_Code。"

    conn.close()
    return output
