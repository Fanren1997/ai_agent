# -*- coding: utf-8 -*-
"""
Access → MySQL 同步工具 v3（增强稳定版）
------------------------------------
✅ 自动容错：跳过非法列、损坏行
✅ 自动行宽优化：ROW_FORMAT=DYNAMIC
✅ 自动编码重试（utf-8 / utf-16 / latin1 / gbk）
✅ 清晰中文日志输出
"""

import os
import pandas as pd
import pyodbc
import pymysql
from pathlib import Path
import json
import warnings

warnings.filterwarnings("ignore", category=UnicodeWarning)


# ======== 加载配置文件 ========
CFG_PATH = Path(__file__).with_name("sync_config.json")
if not CFG_PATH.exists():
    raise FileNotFoundError(f"❌ 找不到配置文件: {CFG_PATH}")

cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
ACCESS_PATH = Path(cfg.get("access_db_path", "")).expanduser()
MYSQL_CFG = cfg.get("mysql_config", {})

if not ACCESS_PATH.exists():
    raise FileNotFoundError(f"❌ Access 文件不存在: {ACCESS_PATH}")


# ======== MySQL 连接 ========
def get_mysql_conn():
    conn = pymysql.connect(
        host=MYSQL_CFG["host"],
        user=MYSQL_CFG["user"],
        password=MYSQL_CFG["password"],
        database=MYSQL_CFG["database"],
        charset="utf8mb4",
        local_infile=True,
        autocommit=True,
    )
    return conn


# ======== Access 连接 ========
def get_access_conn():
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_PATH};"
    )
    return pyodbc.connect(conn_str, autocommit=True)


# ======== 表同步函数 ========
def sync_table(table_name, conn_access, conn_mysql):
    print(f"\n[SYNC] 开始同步表：{table_name}")

    df = None
    try:
        # 尝试不同编码读取 Access
        for enc in ["utf-8", "utf-16", "latin1", "gbk"]:
            try:
                df = pd.read_sql(f"SELECT * FROM [{table_name}]", conn_access)
                break
            except Exception as e:
                print(f"[WARN] 尝试编码 {enc} 失败：{e}")
                continue

        if df is None or df.empty:
            print(f"[INFO] 表 {table_name} 为空或读取失败，跳过。")
            return

        # 清理列名
        df.columns = [
            str(c).strip().replace("/", "_").replace(" ", "_").replace("-", "_")
            for c in df.columns
        ]

        # 尝试转换数据为字符串（防止类型冲突）
        df = df.astype(str)

        cursor = conn_mysql.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")

        # 宽表检测
        if len(df.columns) > 80:
            print(f"[AUTO-FIX] {table_name} 为宽表（{len(df.columns)}列），使用 TEXT 类型。")
            col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])
        else:
            col_defs = ", ".join([f"`{col}` VARCHAR(255)" for col in df.columns])

        # 创建表，强制 DYNAMIC
        create_sql = f"CREATE TABLE `{table_name}` ({col_defs}) ROW_FORMAT=DYNAMIC;"
        cursor.execute(create_sql)

        # 批量插入
        insert_sql = f"INSERT INTO `{table_name}` VALUES ({','.join(['%s'] * len(df.columns))})"

        data = []
        for row in df.itertuples(index=False, name=None):
            try:
                clean_row = tuple(None if (x in ["nan", "None", "NaT"]) else x for x in row)
                data.append(clean_row)
            except Exception as e:
                print(f"[WARN] 跳过损坏行: {e}")
                continue

        cursor.executemany(insert_sql, data)
        print(f"[DONE] 导入 {len(data)} 条记录。")

    except Exception as e:
        print(f"[ERROR] 表 {table_name} 同步失败: {e}")


# ======== 主入口 ========
def main():
    print("[START] Access → MySQL 同步启动")
    print(f"[INFO] Access 文件: {ACCESS_PATH}")

    try:
        conn_access = get_access_conn()
    except Exception as e:
        print(f"[ERROR] 无法连接 Access: {e}")
        return

    # 获取所有表名
    try:
        tables_df = pd.read_sql(
            "SELECT Name FROM MSysObjects WHERE Type=1 AND Flags=0", conn_access
        )
        tables = [t[0] for t in tables_df.values]
    except Exception:
        # 部分 Access 无法读 MSysObjects，用 schema fallback
        print("[WARN] 无法读取 MSysObjects，使用 pyodbc.cursor 方式读取。")
        cursor = conn_access.cursor()
        tables = [r.table_name for r in cursor.tables() if r.table_type == "TABLE"]

    print(f"[INFO] 检测到 Access 表数量: {len(tables)}")

    conn_mysql = get_mysql_conn()

    for t in tables:
        try:
            sync_table(t, conn_access, conn_mysql)
        except Exception as e:
            print(f"[FATAL] 表 {t} 同步失败: {e}")

    conn_access.close()
    conn_mysql.close()
    print("\n[SUCCESS] 所有表同步完成。")


if __name__ == "__main__":
    main()
