# -*- coding: utf-8 -*-
"""
数据库服务模块 · Access Agent
用于 MySQL 连接、SQL 执行与结果返回
支持自动重连与中文日志输出
"""

import pymysql
import pandas as pd
# ✅ 最正确写法（直接从同级文件引入）
from config import MYSQL_CONFIG



def get_connection():
    """
    获取 MySQL 连接对象
    """
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            port=int(MYSQL_CONFIG.get("port", 3306)),
            charset=MYSQL_CONFIG.get("charset", "utf8mb4"),
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


def execute_sql(sql: str):
    """
    执行 SQL 并返回 JSON 结果（列表 + 字典格式）
    """
    conn = get_connection()
    if not conn:
        return {"error": "无法连接数据库"}

    try:
        print(f"✅ 已连接数据库: {MYSQL_CONFIG['database']} at {MYSQL_CONFIG['host']}")
        print(f"🧠 执行 SQL: {sql}")

        df = pd.read_sql(sql, conn)

        # 转换为列表形式输出
        result = df.to_dict(orient="records")
        if not result:
            return {"message": "查询无结果", "result": []}

        print(f"📊 返回 {len(result)} 条记录")
        return result

    except Exception as e:
        print(f"⚠️ SQL 执行错误: {e}")
        return {"error": f"SQL执行错误: {e}"}

    finally:
        conn.close()
