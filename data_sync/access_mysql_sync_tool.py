#!/usr/bin/env python3
"""
Access到MySQL数据同步工具
用于在Windows环境下将Microsoft Access数据库(.accdb)同步到MySQL数据库

作者: Manus AI
版本: 1.0
支持的Python版本: 3.8+
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

try:
    import pyodbc
    import mysql.connector
    import pandas as pd
    from mysql.connector import Error
except ImportError as e:
    print(f"缺少必要的依赖包: {e}")
    print("请在Windows环境下运行以下命令安装依赖:")
    print("pip install pyodbc mysql-connector-python pandas")
    sys.exit(1)


class AccessMySQLSyncTool:
    """Access到MySQL数据同步工具"""
    
    def __init__(self, config_file: str = "sync_config.json"):
        """
        初始化同步工具
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = {}
        self.access_conn = None
        self.mysql_conn = None
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger('AccessMySQLSync')
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(
            f'sync_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        try:
            if not os.path.exists(self.config_file):
                self.logger.warning(f"配置文件 {self.config_file} 不存在，将创建默认配置")
                self._create_default_config()
                return False
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            # 验证配置
            required_keys = ['access_db_path', 'mysql_config', 'sync_tables']
            for key in required_keys:
                if key not in self.config:
                    self.logger.error(f"配置文件缺少必要字段: {key}")
                    return False
                    
            self.logger.info("配置文件加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return False
    
    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "access_db_path": "path/to/your/database.accdb",
            "mysql_config": {
                "host": "localhost",
                "user": "access_user",
                "password": "your_password",
                "database": "access_migration_db",
                "charset": "utf8mb4"
            },
            "sync_tables": [
                {
                    "access_table": "10NC_based",
                    "mysql_table": "10nc_based",
                    "primary_key": "id",
                    "sync_mode": "full"
                }
            ],
            "sync_options": {
                "batch_size": 1000,
                "backup_before_sync": True,
                "verify_data": True,
                "log_level": "INFO"
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            self.logger.info(f"已创建默认配置文件: {self.config_file}")
            self.logger.info("请修改配置文件中的数据库连接信息后重新运行")
        except Exception as e:
            self.logger.error(f"创建默认配置文件失败: {e}")
    
    def connect_access(self) -> bool:
        """
        连接Access数据库
        
        Returns:
            bool: 连接成功返回True，失败返回False
        """
        try:
            access_path = self.config['access_db_path']
            if not os.path.exists(access_path):
                self.logger.error(f"Access数据库文件不存在: {access_path}")
                return False
            
            # 构建连接字符串
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                f'DBQ={access_path};'
            )
            
            self.access_conn = pyodbc.connect(conn_str)
            self.logger.info(f"成功连接到Access数据库: {access_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"连接Access数据库失败: {e}")
            return False
    
    def connect_mysql(self) -> bool:
        """
        连接MySQL数据库
        
        Returns:
            bool: 连接成功返回True，失败返回False
        """
        try:
            mysql_config = self.config['mysql_config']
            self.mysql_conn = mysql.connector.connect(**mysql_config)
            
            if self.mysql_conn.is_connected():
                self.logger.info(f"成功连接到MySQL数据库: {mysql_config['host']}")
                return True
            else:
                self.logger.error("MySQL连接失败")
                return False
                
        except Error as e:
            self.logger.error(f"连接MySQL数据库失败: {e}")
            return False
    
    def get_access_tables(self) -> List[str]:
        """
        获取Access数据库中的所有表名
        
        Returns:
            List[str]: 表名列表
        """
        try:
            cursor = self.access_conn.cursor()
            tables = []
            
            # 获取用户表（排除系统表）
            for table_info in cursor.tables(tableType='TABLE'):
                table_name = table_info.table_name
                if not table_name.startswith('MSys'):
                    tables.append(table_name)
            
            cursor.close()
            self.logger.info(f"发现 {len(tables)} 个用户表: {tables}")
            return tables
            
        except Exception as e:
            self.logger.error(f"获取Access表列表失败: {e}")
            return []
    
    def get_table_structure(self, table_name: str) -> Dict[str, Any]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            Dict: 表结构信息
        """
        try:
            cursor = self.access_conn.cursor()
            
            # 获取列信息
            columns = []
            for column in cursor.columns(table=table_name):
                columns.append({
                    'name': column.column_name,
                    'type': column.type_name,
                    'size': column.column_size,
                    'nullable': column.nullable == 1
                })
            
            cursor.close()
            
            structure = {
                'table_name': table_name,
                'columns': columns,
                'column_count': len(columns)
            }
            
            self.logger.info(f"表 {table_name} 包含 {len(columns)} 个字段")
            return structure
            
        except Exception as e:
            self.logger.error(f"获取表结构失败 {table_name}: {e}")
            return {}
    
    def read_access_data(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        从Access表中读取数据
        
        Args:
            table_name: 表名
            limit: 限制读取的记录数
            
        Returns:
            pd.DataFrame: 数据框
        """
        try:
            sql = f"SELECT * FROM [{table_name}]"
            if limit:
                sql += f" LIMIT {limit}"
            
            df = pd.read_sql(sql, self.access_conn)
            self.logger.info(f"从表 {table_name} 读取了 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"读取Access数据失败 {table_name}: {e}")
            return pd.DataFrame()
    
    def create_mysql_table(self, table_config: Dict[str, Any], structure: Dict[str, Any]) -> bool:
        """
        在MySQL中创建表
        
        Args:
            table_config: 表配置信息
            structure: 表结构信息
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            mysql_table = table_config['mysql_table']
            cursor = self.mysql_conn.cursor()
            
            # 检查表是否存在
            cursor.execute(f"SHOW TABLES LIKE '{mysql_table}'")
            if cursor.fetchone():
                self.logger.info(f"MySQL表 {mysql_table} 已存在")
                cursor.close()
                return True
            
            # 构建CREATE TABLE语句
            columns_sql = []
            for col in structure['columns']:
                col_name = col['name'].replace(' ', '_').replace('-', '_')
                
                # 映射数据类型
                mysql_type = self._map_access_type_to_mysql(col['type'], col['size'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                
                columns_sql.append(f"`{col_name}` {mysql_type} {nullable}")
            
            # 添加主键（如果配置了）
            if 'primary_key' in table_config and table_config['primary_key']:
                pk_col = table_config['primary_key'].replace(' ', '_').replace('-', '_')
                columns_sql.append(f"PRIMARY KEY (`{pk_col}`)")
            
            create_sql = f"""
            CREATE TABLE `{mysql_table}` (
                {', '.join(columns_sql)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_sql)
            self.mysql_conn.commit()
            cursor.close()
            
            self.logger.info(f"成功创建MySQL表: {mysql_table}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建MySQL表失败: {e}")
            return False
    
    def _map_access_type_to_mysql(self, access_type: str, size: int) -> str:
        """
        将Access数据类型映射到MySQL数据类型
        
        Args:
            access_type: Access数据类型
            size: 字段大小
            
        Returns:
            str: MySQL数据类型
        """
        type_mapping = {
            'VARCHAR': f'VARCHAR({min(size, 255)})',
            'LONGCHAR': 'TEXT',
            'INTEGER': 'INT',
            'SMALLINT': 'SMALLINT',
            'SINGLE': 'FLOAT',
            'DOUBLE': 'DOUBLE',
            'CURRENCY': 'DECIMAL(19,4)',
            'DATETIME': 'DATETIME',
            'BIT': 'TINYINT(1)',
            'LONGBINARY': 'LONGBLOB',
            'MEMO': 'LONGTEXT'
        }
        
        return type_mapping.get(access_type.upper(), f'VARCHAR({min(size, 255)})')
    
    def sync_table_data(self, table_config: Dict[str, Any]) -> bool:
        """
        同步表数据
        
        Args:
            table_config: 表配置信息
            
        Returns:
            bool: 同步成功返回True
        """
        try:
            access_table = table_config['access_table']
            mysql_table = table_config['mysql_table']
            sync_mode = table_config.get('sync_mode', 'full')
            batch_size = self.config.get('sync_options', {}).get('batch_size', 1000)
            
            self.logger.info(f"开始同步表数据: {access_table} -> {mysql_table}")
            
            # 读取Access数据
            df = self.read_access_data(access_table)
            if df.empty:
                self.logger.warning(f"表 {access_table} 没有数据")
                return True
            
            # 清理列名
            df.columns = [col.replace(' ', '_').replace('-', '_') for col in df.columns]
            
            # 处理特殊值
            df = df.fillna('')  # 将NaN替换为空字符串
            
            cursor = self.mysql_conn.cursor()
            
            # 如果是全量同步，先清空MySQL表
            if sync_mode == 'full':
                cursor.execute(f"DELETE FROM `{mysql_table}`")
                self.logger.info(f"已清空MySQL表: {mysql_table}")
            
            # 批量插入数据
            total_rows = len(df)
            inserted_rows = 0
            
            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]
                
                # 构建INSERT语句
                columns = ', '.join([f'`{col}`' for col in batch_df.columns])
                placeholders = ', '.join(['%s'] * len(batch_df.columns))
                insert_sql = f"INSERT INTO `{mysql_table}` ({columns}) VALUES ({placeholders})"
                
                # 准备数据
                data_tuples = [tuple(row) for row in batch_df.values]
                
                cursor.executemany(insert_sql, data_tuples)
                inserted_rows += len(data_tuples)
                
                self.logger.info(f"已插入 {inserted_rows}/{total_rows} 条记录")
            
            self.mysql_conn.commit()
            cursor.close()
            
            self.logger.info(f"表 {access_table} 同步完成，共同步 {inserted_rows} 条记录")
            return True
            
        except Exception as e:
            self.logger.error(f"同步表数据失败: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def verify_sync_result(self, table_config: Dict[str, Any]) -> bool:
        """
        验证同步结果
        
        Args:
            table_config: 表配置信息
            
        Returns:
            bool: 验证通过返回True
        """
        try:
            access_table = table_config['access_table']
            mysql_table = table_config['mysql_table']
            
            # 获取Access表记录数
            cursor = self.access_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM [{access_table}]")
            access_count = cursor.fetchone()[0]
            cursor.close()
            
            # 获取MySQL表记录数
            cursor = self.mysql_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM `{mysql_table}`")
            mysql_count = cursor.fetchone()[0]
            cursor.close()
            
            if access_count == mysql_count:
                self.logger.info(f"数据验证通过: {access_table}({access_count}) = {mysql_table}({mysql_count})")
                return True
            else:
                self.logger.warning(f"数据验证失败: {access_table}({access_count}) != {mysql_table}({mysql_count})")
                return False
                
        except Exception as e:
            self.logger.error(f"验证同步结果失败: {e}")
            return False
    
    def run_sync(self) -> bool:
        """
        运行完整的同步流程
        
        Returns:
            bool: 同步成功返回True
        """
        try:
            self.logger.info("开始运行Access到MySQL数据同步")
            
            # 加载配置
            if not self.load_config():
                return False
            
            # 连接数据库
            if not self.connect_access():
                return False
                
            if not self.connect_mysql():
                return False
            
            # 获取要同步的表
            sync_tables = self.config['sync_tables']
            success_count = 0
            total_count = len(sync_tables)
            
            for table_config in sync_tables:
                try:
                    access_table = table_config['access_table']
                    self.logger.info(f"处理表: {access_table}")
                    
                    # 获取表结构
                    structure = self.get_table_structure(access_table)
                    if not structure:
                        continue
                    
                    # 创建MySQL表
                    if not self.create_mysql_table(table_config, structure):
                        continue
                    
                    # 同步数据
                    if not self.sync_table_data(table_config):
                        continue
                    
                    # 验证结果
                    if self.config.get('sync_options', {}).get('verify_data', True):
                        self.verify_sync_result(table_config)
                    
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"处理表 {table_config.get('access_table', 'unknown')} 时出错: {e}")
                    continue
            
            self.logger.info(f"同步完成: {success_count}/{total_count} 个表同步成功")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"同步流程执行失败: {e}")
            return False
            
        finally:
            # 关闭连接
            if self.access_conn:
                self.access_conn.close()
            if self.mysql_conn:
                self.mysql_conn.close()
    
    def list_access_tables(self):
        """列出Access数据库中的所有表"""
        if not self.load_config():
            return
            
        if not self.connect_access():
            return
        
        tables = self.get_access_tables()
        print("\nAccess数据库中的表:")
        print("-" * 50)
        for i, table in enumerate(tables, 1):
            structure = self.get_table_structure(table)
            record_count = 0
            try:
                cursor = self.access_conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                record_count = cursor.fetchone()[0]
                cursor.close()
            except:
                pass
            
            print(f"{i:2d}. {table:<30} ({structure.get('column_count', 0)} 字段, {record_count} 记录)")
        
        if self.access_conn:
            self.access_conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Access到MySQL数据同步工具')
    parser.add_argument('--config', '-c', default='sync_config.json', help='配置文件路径')
    parser.add_argument('--list-tables', '-l', action='store_true', help='列出Access数据库中的所有表')
    parser.add_argument('--sync', '-s', action='store_true', help='执行数据同步')
    
    args = parser.parse_args()
    
    tool = AccessMySQLSyncTool(args.config)
    
    if args.list_tables:
        tool.list_access_tables()
    elif args.sync:
        success = tool.run_sync()
        sys.exit(0 if success else 1)
    else:
        print("请指定操作: --list-tables 或 --sync")
        parser.print_help()


if __name__ == '__main__':
    main()

