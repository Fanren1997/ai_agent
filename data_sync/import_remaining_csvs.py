import os
import re
import csv
import mysql.connector
from datetime import datetime

CSV_FILES = [
    ("12NCspec_based", "/home/ubuntu/12NCspec_based.csv"),
    ("12NCspec_based2", "/home/ubuntu/12NCspec_based2.csv"),
    ("12NCspec_based3", "/home/ubuntu/12NCspec_based3.csv"),
]

def sanitize_name(name, existing_names=None):
    name = name.replace("[", "").replace("]", "")
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if existing_names is not None:
        base = name or "column"
        new_name = base
        i = 1
        while new_name in existing_names:
            new_name = f"{base}_{i}"
            i += 1
        return new_name
    return name


def connect_db():
    return mysql.connector.connect(
        host='localhost',
        user='access_user',
        password='wvqbIcZwf5/qgm8V',
        database='access_migration_db'
    )


def get_table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    return [row[0] for row in cursor.fetchall()]


def import_csv(table_name_raw, csv_path, cnx):
    table_name = sanitize_name(table_name_raw)
    cursor = cnx.cursor()
    
    # 检查表是否存在
    try:
        table_columns = get_table_columns(cursor, table_name)
    except mysql.connector.Error:
        print(f"表 {table_name} 不存在，跳过导入")
        return

    if not os.path.exists(csv_path):
        print(f"CSV文件不存在: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        # Map headers to sanitized MySQL column names
        sanitized_headers = []
        used = set()
        for h in headers:
            col = sanitize_name(h.strip(), used)
            used.add(col)
            sanitized_headers.append(col)

        # Choose only columns that exist in table
        insert_cols = [h for h in sanitized_headers if h in table_columns]
        if not insert_cols:
            print(f"表{table_name}没有匹配到任何列，跳过。")
            return

        placeholders = ",".join(["%s"] * len(insert_cols))
        cols_joined = ",".join([f"`{c}`" for c in insert_cols])
        sql = f"INSERT INTO `{table_name}` ({cols_joined}) VALUES ({placeholders})"

        batch = []
        batch_size = 500
        count = 0
        for row in reader:
            # Pad or trim row length to headers length
            if len(row) < len(sanitized_headers):
                row += [None] * (len(sanitized_headers) - len(row))
            elif len(row) > len(sanitized_headers):
                row = row[:len(sanitized_headers)]
            data = []
            for c in insert_cols:
                idx = sanitized_headers.index(c)
                val = row[idx]
                # Normalize empty strings to None
                if val == '':
                    val = None
                
                # Handle datetime conversion for date columns
                if ('Date' in c or 'date' in c.lower()) and val is not None:
                    try:
                        # Attempt to parse common Access datetime formats
                        if re.match(r'^\d{1,2}/\d{1,2}/\d{2} \d{1,2}:\d{2}:\d{2}$', val):
                            val = datetime.strptime(val, '%m/%d/%y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                        elif re.match(r'^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}:\d{2}$', val):
                            val = datetime.strptime(val, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$', val):
                            val = datetime.strptime(val, '%m/%d/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                        elif re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', val):
                            val = datetime.strptime(val, '%m/%d/%y').strftime('%Y-%m-%d %H:%M:%S')
                        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val):
                            val = datetime.strptime(val, '%m/%d/%Y').strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        print(f"Warning: Could not parse datetime value '{val}' for column '{c}'. Setting to None.")
                        val = None

                data.append(val)
            batch.append(tuple(data))
            if len(batch) >= batch_size:
                try:
                    cursor.executemany(sql, batch)
                    count += len(batch)
                    print(f"已导入 {count} 行 -> {table_name}")
                    batch.clear()
                except mysql.connector.Error as e:
                    print(f"导入批次失败: {e}")
                    batch.clear()
        if batch:
            try:
                cursor.executemany(sql, batch)
                count += len(batch)
                print(f"已导入 {count} 行 -> {table_name}")
            except mysql.connector.Error as e:
                print(f"导入最后批次失败: {e}")
        cnx.commit()


def main():
    cnx = connect_db()
    try:
        for tname, path in CSV_FILES:
            print(f"开始导入: {tname} from {path}")
            import_csv(tname, path, cnx)
    finally:
        cnx.close()

if __name__ == '__main__':
    main()

