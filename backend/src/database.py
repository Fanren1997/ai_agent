import mysql.connector
from mysql.connector import Error
from src.config import Config

class DatabaseManager:
    def __init__(self):
        self.config = {
            'host': Config.MYSQL_HOST,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DATABASE,
            'charset': 'utf8mb4'
        }
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            connection = mysql.connector.connect(**self.config)
            return connection
        except Error as e:
            print(f"数据库连接错误: {e}")
            return None
    
    def execute_query(self, query, params=None):
        """执行查询并返回结果"""
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"查询执行错误: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def execute_update(self, query, params=None):
        """执行更新操作"""
        connection = self.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            return True
        except Error as e:
            print(f"更新执行错误: {e}")
            connection.rollback()
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_tables(self):
        """获取所有表名"""
        query = "SHOW TABLES"
        result = self.execute_query(query)
        if result:
            return [list(row.values())[0] for row in result]
        return []
    
    def get_table_columns(self, table_name):
        """获取表的列信息"""
        query = f"SHOW COLUMNS FROM `{table_name}`"
        return self.execute_query(query)
    
    def get_table_count(self, table_name):
        """获取表的记录数"""
        query = f"SELECT COUNT(*) as count FROM `{table_name}`"
        result = self.execute_query(query)
        if result:
            return result[0]['count']
        return 0

# 全局数据库管理器实例
db_manager = DatabaseManager()

