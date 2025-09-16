# Access到MySQL数据同步工具使用指南

## 概述

这是一个专门用于将Microsoft Access数据库(.accdb)中的数据同步到MySQL数据库的工具。该工具设计用于Windows环境，支持自动表结构创建、批量数据导入、数据验证等功能。

## 系统要求

### 硬件要求
- CPU: 1GHz以上
- 内存: 2GB以上
- 存储: 500MB可用空间

### 软件要求
- **操作系统**: Windows 7/8/10/11 (32位或64位)
- **Python**: 3.8或更高版本
- **Microsoft Access数据库引擎**: 以下任一组件
  - Microsoft Office Access (任意版本)
  - Microsoft Access Database Engine 2016 Redistributable

### Python依赖包
- `pyodbc`: 用于连接Access数据库
- `mysql-connector-python`: 用于连接MySQL数据库
- `pandas`: 用于数据处理
- `openpyxl`: 用于Excel文件处理

## 安装步骤

### 1. 安装Python
1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载Python 3.8或更高版本
3. 安装时勾选"Add Python to PATH"选项

### 2. 安装Microsoft Access数据库引擎
如果您的系统中没有安装Microsoft Office Access，需要安装Access数据库引擎：

1. 访问 [Microsoft下载中心](https://www.microsoft.com/en-us/download/details.aspx?id=54920)
2. 下载"Microsoft Access Database Engine 2016 Redistributable"
3. 根据您的系统选择32位或64位版本
4. 运行安装程序完成安装

### 3. 运行自动安装脚本
1. 将所有工具文件复制到一个文件夹中
2. 双击运行 `windows_sync_setup.bat`
3. 脚本会自动安装所需的Python包并检查系统环境

### 4. 手动安装依赖包（可选）
如果自动安装脚本失败，可以手动安装：

```cmd
pip install pyodbc mysql-connector-python pandas openpyxl
```

## 配置说明

### 1. 创建配置文件
将 `sync_config_template.json` 复制为 `sync_config.json`，然后修改其中的配置信息。

### 2. 配置参数说明

#### 数据库连接配置
```json
{
    "access_db_path": "C:\\path\\to\\your\\database.accdb",
    "mysql_config": {
        "host": "localhost",
        "user": "access_user", 
        "password": "your_password",
        "database": "access_migration_db",
        "charset": "utf8mb4",
        "port": 3306
    }
}
```

- `access_db_path`: Access数据库文件的完整路径
- `mysql_config`: MySQL数据库连接信息

#### 同步表配置
```json
{
    "sync_tables": [
        {
            "access_table": "10NC_based",
            "mysql_table": "10nc_based", 
            "primary_key": "Project_code",
            "sync_mode": "full",
            "description": "主要产品数据表"
        }
    ]
}
```

- `access_table`: Access中的源表名
- `mysql_table`: MySQL中的目标表名
- `primary_key`: 主键字段名（可选）
- `sync_mode`: 同步模式（full=全量同步，incremental=增量同步）
- `description`: 表描述信息

#### 同步选项
```json
{
    "sync_options": {
        "batch_size": 1000,
        "backup_before_sync": true,
        "verify_data": true,
        "log_level": "INFO",
        "max_retries": 3,
        "retry_delay": 5,
        "connection_timeout": 30
    }
}
```

- `batch_size`: 批量插入的记录数
- `backup_before_sync`: 同步前是否备份
- `verify_data`: 是否验证数据完整性
- `log_level`: 日志级别
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟（秒）
- `connection_timeout`: 连接超时时间（秒）

## 使用方法

### 1. 查看Access数据库中的表
```cmd
python access_mysql_sync_tool.py --list-tables
```

这个命令会显示Access数据库中所有的用户表，包括表名、字段数量和记录数。

### 2. 执行数据同步
```cmd
python access_mysql_sync_tool.py --sync
```

这个命令会根据配置文件执行完整的数据同步流程。

### 3. 指定配置文件
```cmd
python access_mysql_sync_tool.py --config my_config.json --sync
```

使用自定义的配置文件执行同步。

## 同步流程

### 1. 连接验证
- 验证Access数据库文件是否存在
- 测试Access数据库连接
- 测试MySQL数据库连接

### 2. 表结构处理
- 读取Access表结构
- 自动映射数据类型到MySQL
- 在MySQL中创建对应的表结构

### 3. 数据同步
- 从Access表中读取数据
- 清理和转换数据格式
- 批量插入到MySQL表中
- 显示同步进度

### 4. 数据验证
- 比较源表和目标表的记录数
- 验证数据完整性
- 生成同步报告

## 数据类型映射

| Access类型 | MySQL类型 | 说明 |
|------------|-----------|------|
| VARCHAR | VARCHAR(n) | 可变长度字符串 |
| LONGCHAR | TEXT | 长文本 |
| INTEGER | INT | 整数 |
| SMALLINT | SMALLINT | 小整数 |
| SINGLE | FLOAT | 单精度浮点数 |
| DOUBLE | DOUBLE | 双精度浮点数 |
| CURRENCY | DECIMAL(19,4) | 货币类型 |
| DATETIME | DATETIME | 日期时间 |
| BIT | TINYINT(1) | 布尔值 |
| LONGBINARY | LONGBLOB | 二进制大对象 |
| MEMO | LONGTEXT | 备注字段 |

## 日志和监控

### 日志文件
工具会自动生成日志文件，文件名格式为：`sync_log_YYYYMMDD_HHMMSS.log`

### 日志内容包括
- 连接状态信息
- 表处理进度
- 数据同步统计
- 错误和警告信息
- 验证结果

### 监控同步进度
```
2024-01-20 10:30:15 - AccessMySQLSync - INFO - 开始同步表数据: 10NC_based -> 10nc_based
2024-01-20 10:30:16 - AccessMySQLSync - INFO - 从表 10NC_based 读取了 24329 条记录
2024-01-20 10:30:17 - AccessMySQLSync - INFO - 已插入 1000/24329 条记录
2024-01-20 10:30:18 - AccessMySQLSync - INFO - 已插入 2000/24329 条记录
...
2024-01-20 10:31:45 - AccessMySQLSync - INFO - 表 10NC_based 同步完成，共同步 24329 条记录
```

## 故障排除

### 常见问题

#### 1. "未检测到Python"
**解决方案**: 
- 确保Python已正确安装
- 检查Python是否已添加到系统PATH环境变量

#### 2. "pyodbc安装失败"
**解决方案**:
- 安装Microsoft Visual C++ Redistributable
- 安装Microsoft Access Database Engine
- 使用conda安装: `conda install pyodbc`

#### 3. "无法检测到Microsoft Access ODBC驱动程序"
**解决方案**:
- 安装Microsoft Office Access
- 或安装Microsoft Access Database Engine 2016 Redistributable
- 确保安装的版本（32位/64位）与Python版本匹配

#### 4. "Access数据库文件不存在"
**解决方案**:
- 检查配置文件中的路径是否正确
- 确保使用完整的绝对路径
- 检查文件权限

#### 5. "MySQL连接失败"
**解决方案**:
- 检查MySQL服务是否启动
- 验证连接参数（主机、端口、用户名、密码）
- 检查防火墙设置
- 确保用户有足够的权限

#### 6. "数据类型转换错误"
**解决方案**:
- 检查源数据中是否有特殊字符
- 修改字段映射配置
- 手动调整表结构

### 调试技巧

#### 1. 启用详细日志
修改配置文件中的日志级别：
```json
{
    "sync_options": {
        "log_level": "DEBUG"
    }
}
```

#### 2. 小批量测试
减少批量大小进行测试：
```json
{
    "sync_options": {
        "batch_size": 100
    }
}
```

#### 3. 单表测试
临时修改配置文件，只同步一个表进行测试。

## 性能优化

### 1. 批量大小调整
- 大表使用较大的批量大小（1000-5000）
- 小表使用较小的批量大小（100-500）
- 根据内存情况调整

### 2. 网络优化
- 确保MySQL服务器网络连接稳定
- 考虑使用本地MySQL服务器
- 调整连接超时时间

### 3. 数据库优化
- 在同步前禁用MySQL表的索引
- 同步完成后重建索引
- 使用InnoDB存储引擎

## 安全建议

### 1. 数据库安全
- 使用专门的同步用户账户
- 限制用户权限到最小必要范围
- 使用强密码

### 2. 文件安全
- 保护配置文件，避免密码泄露
- 定期更换数据库密码
- 备份重要数据

### 3. 网络安全
- 使用SSL连接MySQL（生产环境）
- 限制网络访问范围
- 监控异常访问

## 维护和更新

### 定期维护任务
1. **检查日志文件**: 定期查看同步日志，及时发现问题
2. **清理临时文件**: 删除过期的日志文件和临时数据
3. **更新配置**: 根据数据结构变化更新配置文件
4. **性能监控**: 监控同步时间和资源使用情况

### 版本更新
1. **备份配置**: 更新前备份现有配置文件
2. **测试新版本**: 在测试环境中验证新版本
3. **逐步部署**: 先在非关键环境部署，再推广到生产环境

## 技术支持

### 获取帮助
如果遇到问题，请按以下步骤获取帮助：

1. **查看日志文件**: 检查详细的错误信息
2. **检查配置**: 验证所有配置参数是否正确
3. **测试连接**: 分别测试Access和MySQL连接
4. **查看文档**: 参考本文档的故障排除部分

### 联系信息
- 工具作者: Manus AI
- 版本: 1.0
- 更新日期: 2024年

## 许可证

本工具仅供学习和内部使用，请遵守相关软件的许可协议。

## 更新历史

### 版本 1.0 (2024-01-20)
- 初始版本发布
- 支持Access到MySQL的完整数据同步
- 包含自动表结构创建功能
- 支持批量数据处理和验证
- 提供详细的日志记录和错误处理

