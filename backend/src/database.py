# backend/src/database.py
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from pathlib import Path

# 加载 .env
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)


class DatabaseManager:
    def __init__(self):
        self.config = {
            "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", ""),
        }

    def get_connection(self):
        """获取 MySQL 连接"""
        try:
            conn = mysql.connector.connect(**self.config)
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"❌ 数据库连接错误: {e}")
        return None

    def execute_query(self, query, params=None):
        """执行 SQL 查询"""
        conn = self.get_connection()
        if conn is None:
            raise Exception("无法连接数据库")
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
        except Error as e:
            raise Exception(f"SQL 执行错误: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_tables(self):
        """获取所有表名"""
        conn = self.get_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables


# 全局实例
db_manager = DatabaseManager()


def check_db_connection():
    """健康检查：测试 MySQL 是否可连接"""
    try:
        conn = db_manager.get_connection()
        if conn:
            conn.close()
            print("✅ 数据库连接测试通过")
            return True
        else:
            print("❌ 无法连接到数据库")
            return False
    except Exception as e:
        print(f"❌ 数据库健康检查失败: {e}")
        return False
