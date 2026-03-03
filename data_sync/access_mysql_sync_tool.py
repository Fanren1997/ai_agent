# -*- coding: utf-8 -*-
"""
Access -> MySQL sync tool (Windows friendly).
Features:
- Removes emojis to avoid console issues.
- Falls back to chunked import for wide tables.
- Cleans column names and trims null chars.
"""

from __future__ import annotations

import io
import os
import csv
import time
import math
import json
import warnings
import traceback
import multiprocessing as mp
from pathlib import Path

import pandas as pd
import pyodbc
import pymysql

# Force UTF-8 stdout/stderr to avoid garbled logs on Windows consoles.
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

warnings.filterwarnings("ignore")

CFG_PATH = Path(__file__).with_name("sync_config.json")
if not CFG_PATH.exists():
    raise FileNotFoundError(f"[ERROR] Config file not found: {CFG_PATH}")

cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))

ACCESS_PATH = Path(cfg["access_db_path"]).expanduser()
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD") or cfg.get("access_password", "")
MYSQL_CFG = dict(cfg["mysql_config"])
if os.getenv("MYSQL_PASSWORD"):
    MYSQL_CFG["password"] = os.getenv("MYSQL_PASSWORD")
WORKERS = int(cfg.get("workers") or 4)


# ==========================================================
# MySQL connection
# ==========================================================
def get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_CFG["host"],
        user=MYSQL_CFG["user"],
        password=MYSQL_CFG["password"],
        database=MYSQL_CFG["database"],
        charset="utf8mb4",
        autocommit=True,
        local_infile=True,
    )


# ==========================================================
# Access connection
# ==========================================================
def get_access_conn():
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_PATH};"
    )
    if ACCESS_PASSWORD:
        conn_str += f"PWD={ACCESS_PASSWORD};"

    return pyodbc.connect(conn_str, autocommit=True)


# ==========================================================
# Helpers: clean column names
# ==========================================================
def clean_name(name: str):
    return (
        str(name).strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "_")
        .replace("%", "_")
        .replace("(", "_")
        .replace(")", "_")
    )


def ensure_unique_columns(cols):
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    return new_cols


def export_to_csv(df: pd.DataFrame, filename: str):
    if df is None or df.empty:
        raise ValueError("DataFrame is empty, cannot export CSV")

    path = Path(filename)

    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    return path


# ==========================================================
# Wide table import
# ==========================================================
def import_wide_table(df, clean_table, conn_mysql):
    cursor = conn_mysql.cursor()
    ncols = len(df.columns)
    parts = math.ceil(ncols / 100)

    print(f"[INFO] {clean_table}: {ncols} columns -> split into {parts} sub tables")

    for i in range(parts):
        start = i * 100
        end = min((i + 1) * 100, ncols)

        sub_df = df.iloc[:, start:end]
        sub_table = f"{clean_table}_part{i+1}"

        cursor.execute(f"DROP TABLE IF EXISTS `{sub_table}`;")
        col_defs = ", ".join(f"`{c}` TEXT" for c in sub_df.columns)
        cursor.execute(f"CREATE TABLE `{sub_table}` ({col_defs})")

        try:
            temp_csv = export_to_csv(sub_df, f"{sub_table}.csv")
        except Exception as e:
            print(f"[ERROR] Export CSV failed: {e}")
            continue

        try:
            load_sql = (
                "LOAD DATA LOCAL INFILE %s INTO TABLE `{}` "
                "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
                "LINES TERMINATED BY '\\n' IGNORE 1 LINES".format(sub_table)
            )
            cursor.execute(load_sql, (str(temp_csv),))
        except Exception as e:
            print(f"[WARN] LOAD DATA failed, fallback to executemany: {e}")
            cols = ",".join(f"`{c}`" for c in sub_df.columns)
            placeholders = ",".join(["%s"] * len(sub_df.columns))
            sql = f"INSERT INTO `{sub_table}` ({cols}) VALUES ({placeholders})"
            cursor.executemany(sql, sub_df.itertuples(index=False, name=None))

        temp_csv.unlink(missing_ok=True)
        print(f"[OK] {sub_table} imported (columns {start+1}-{end})")


# ==========================================================
# Recover Access table by columns (handle 22012/22018 errors)
# ==========================================================
def recover_table_columns(table, conn_access):
    print(f"[WARN] {table}: column-by-column recovery mode...")

    cur = conn_access.cursor()
    cur.execute(f"SELECT * FROM [{table}] WHERE 1=0")
    columns = [d[0] for d in cur.description]

    data_dict = {}

    for col in columns:
        try:
            cur.execute(f"SELECT [{col}] FROM [{table}]")
            vals = []
            for r in cur.fetchall():
                v = r[0]
                if v is None:
                    vals.append(None)
                else:
                    vals.append(str(v).replace("\x00", "").strip())
            data_dict[col] = vals

        except Exception as e:
            print(f"[WARN] Column {col} cannot be read: {e}")

    if not data_dict:
        print(f"[ERROR] {table}: no data recovered")
        return None

    max_len = max(len(v) for v in data_dict.values())
    for k, v in data_dict.items():
        if len(v) < max_len:
            v.extend([None] * (max_len - len(v)))

    df = pd.DataFrame(data_dict)
    print(f"[OK] {table}: recovered by columns, total {len(df)} rows")
    return df


# ==========================================================
# Main sync logic
# ==========================================================
def sync_table(table_name):
    try:
        conn_access = get_access_conn()
        conn_mysql = get_mysql_conn()

        print("\n==============================")
        print(f"[SYNC] Start syncing table: {table_name}")

        cursor = conn_mysql.cursor()
        clean_table = clean_name(table_name)

        df = None

        # Primary path: direct read
        try:
            df = pd.read_sql(f"SELECT * FROM [{table_name}]", conn_access)
        except Exception as e:
            print(f"[WARN] Direct read failed for {table_name}: {e}")
            df = recover_table_columns(table_name, conn_access)

        if df is None:
            print(f"[WARN] {table_name} has no data, skipped")
            return

        df.columns = [clean_name(c) for c in df.columns]
        df.columns = ensure_unique_columns(df.columns)
        df = df.map(lambda x: str(x).replace("\x00", "").strip() if x is not None and pd.notnull(x) else None)

        cursor.execute(f"DROP TABLE IF EXISTS `{clean_table}`;")

        if len(df.columns) > 100:
            import_wide_table(df, clean_table, conn_mysql)
        else:
            col_defs = ", ".join(f"`{c}` TEXT" for c in df.columns)
            cursor.execute(f"CREATE TABLE `{clean_table}` ({col_defs})")

            temp_csv = export_to_csv(df, f"{clean_table}.csv")

            try:
                load_sql = (
                    "LOAD DATA LOCAL INFILE %s INTO TABLE `{}` "
                    "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
                    "LINES TERMINATED BY '\\n' IGNORE 1 LINES".format(clean_table)
                )
                cursor.execute(load_sql, (str(temp_csv),))
            except Exception as e:
                print(f"[WARN] LOAD DATA failed, fallback to executemany: {e}")
                cols = ",".join(f"`{c}`" for c in df.columns)
                placeholders = ",".join(["%s"] * len(df.columns))
                sql = f"INSERT INTO `{clean_table}` ({cols}) VALUES ({placeholders})"
                cursor.executemany(sql, df.itertuples(index=False, name=None))

            temp_csv.unlink(missing_ok=True)

        print(f"[OK] {clean_table} sync done, total {len(df)} rows")

    except Exception as e:
        print(f"[FATAL] {table_name} sync failed: {e}")
        traceback.print_exc()


# ==========================================================
# Entry point
# ==========================================================
def main():
    print("[START] Access -> MySQL sync starting")

    conn_access = get_access_conn()
    cursor = conn_access.cursor()
    tables = [r.table_name for r in cursor.tables() if r.table_type == "TABLE"]

    print(f"[INFO] Found {len(tables)} tables, using {WORKERS} processes")

    with mp.Pool(processes=WORKERS) as pool:
        pool.map(sync_table, tables)

    print("[SUCCESS] All tables synced")


if __name__ == "__main__":
    main()
