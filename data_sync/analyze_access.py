import sys
from access_parser import AccessParser

def analyze_accdb(file_path):
    try:
        parser = AccessParser(file_path)
        tables = parser.get_table_names()
        print(f"数据库中的表: {tables}")

        for table_name in tables:
            print(f"\n表名: {table_name}")
            columns = parser.get_columns(table_name)
            print(f"  列: {columns}")
            # 尝试读取前5行数据，避免大表一次性读取过多数据
            try:
                data = parser.get_rows(table_name, limit=5)
                print(f"  前5行数据: {data}")
            except Exception as e:
                print(f"  读取表 {table_name} 数据失败: {e}")

    except Exception as e:
        print(f"分析Access数据库失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_access.py <accdb文件路径>")
        sys.exit(1)
    file_path = sys.argv[1]
    analyze_accdb(file_path)


