# AI智慧体系统部署指南

## 系统概述
AI智慧体数据查询系统是一个基于Flask后端和React前端的Web应用，支持MySQL数据库查询、智能分析和数据导出功能。

## 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB以上
- 存储: 10GB以上可用空间

### 软件要求
- 操作系统: Ubuntu 20.04+ / CentOS 7+ / Windows 10+
- Python: 3.8+
- Node.js: 16+
- MySQL: 8.0+

## 部署步骤

### 1. 环境准备

#### 安装MySQL
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mysql-server

# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### 安装Python和Node.js
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip nodejs npm

# 或使用包管理器安装最新版本
```

### 2. 数据库设置

#### 创建数据库和用户
```sql
-- 登录MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE access_migration_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（请修改密码）
CREATE USER 'access_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- 授权
GRANT ALL PRIVILEGES ON access_migration_db.* TO 'access_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 应用部署

#### 下载项目文件
将以下文件复制到服务器：
- `/home/ubuntu/ai_smart_system/` - 完整的Flask应用
- `/home/ubuntu/ai_smart_frontend/` - React前端源码（可选，用于开发）

#### 安装后端依赖
```bash
cd ai_smart_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 配置环境变量
```bash
# 创建环境配置文件
cat > .env << EOF
MYSQL_HOST=localhost
MYSQL_USER=access_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=access_migration_db
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1
EOF
```

#### 数据导入
```bash
# 如果有Access数据库文件，使用以下步骤导入
# 1. 安装mdbtools
sudo apt-get install mdbtools

# 2. 运行数据导入脚本
python3 create_mysql_tables.py
python3 import_access_csvs.py
```

### 4. 启动应用

#### 开发模式
```bash
cd ai_smart_system
source venv/bin/activate
python src/main.py
```

#### 生产模式（推荐）
```bash
# 安装gunicorn
pip install gunicorn

# 启动应用
cd ai_smart_system
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
```

#### 使用systemd服务（推荐）
```bash
# 创建服务文件
sudo tee /etc/systemd/system/ai-smart-system.service << EOF
[Unit]
Description=AI Smart System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai_smart_system
Environment=PATH=/home/ubuntu/ai_smart_system/venv/bin
ExecStart=/home/ubuntu/ai_smart_system/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable ai-smart-system
sudo systemctl start ai-smart-system
```

### 5. 反向代理（可选）

#### 使用Nginx
```bash
# 安装Nginx
sudo apt-get install nginx

# 配置Nginx
sudo tee /etc/nginx/sites-available/ai-smart-system << EOF
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/ai-smart-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 配置说明

### 数据库配置
修改 `src/config.py` 中的数据库连接信息：
```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'access_user'
MYSQL_PASSWORD = 'your_password'
MYSQL_DATABASE = 'access_migration_db'
```

### AI功能配置
如需启用AI功能，需要配置OpenAI API：
```python
OPENAI_API_KEY = 'your_openai_api_key'
OPENAI_API_BASE = 'https://api.openai.com/v1'
```

注意：当前系统支持的AI模型：
- gpt-4.1-mini
- gpt-4.1-nano  
- gemini-2.5-flash

## 访问应用

部署完成后，可通过以下方式访问：
- 直接访问: http://localhost:5000
- 通过域名: http://your_domain.com（如配置了Nginx）

## 功能说明

### 主要功能
1. **数据查询**: 支持SQL查询和自然语言查询
2. **智能对话**: AI助手对话功能
3. **数据导出**: 支持CSV和Excel格式导出
4. **数据分析**: 基础数据统计和分析

### 使用方法
1. 选择数据表
2. 输入SQL查询或自然语言问题
3. 查看查询结果
4. 导出数据或进行进一步分析

## 故障排除

### 常见问题

#### 1. 数据库连接失败
- 检查MySQL服务是否启动
- 验证数据库用户名和密码
- 确认数据库存在

#### 2. AI功能不可用
- 检查OpenAI API密钥配置
- 确认使用支持的AI模型
- 检查网络连接

#### 3. 前端页面无法加载
- 检查Flask应用是否正常启动
- 确认静态文件是否正确部署
- 检查端口是否被占用

### 日志查看
```bash
# 查看应用日志
journalctl -u ai-smart-system -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 安全建议

1. **数据库安全**
   - 使用强密码
   - 限制数据库用户权限
   - 定期备份数据

2. **应用安全**
   - 使用HTTPS（生产环境）
   - 定期更新依赖包
   - 配置防火墙

3. **API安全**
   - 保护API密钥
   - 设置请求频率限制
   - 监控API使用情况

## 维护和更新

### 定期维护
- 定期备份数据库
- 更新系统依赖
- 监控系统性能
- 清理临时文件

### 更新应用
```bash
# 停止服务
sudo systemctl stop ai-smart-system

# 更新代码
# (复制新的应用文件)

# 更新依赖
cd ai_smart_system
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start ai-smart-system
```

## 技术支持

如遇到问题，请检查：
1. 系统日志
2. 数据库连接
3. 网络配置
4. 依赖版本

系统已经过测试，核心功能运行正常。如需定制开发或技术支持，请联系开发团队。

