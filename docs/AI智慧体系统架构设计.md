# AI智慧体系统架构设计

## 系统概述

本系统是一个基于Web的AI智慧体，用于查询、分析和管理从Microsoft Access数据库迁移到MySQL的数据。系统提供智能查询、数据总结和导出功能。

## 技术栈

### 后端
- **框架**: Flask (Python)
- **数据库**: MySQL 8.0
- **AI服务**: OpenAI API
- **数据处理**: pandas, numpy
- **数据库连接**: mysql-connector-python
- **跨域支持**: Flask-CORS

### 前端
- **框架**: React
- **UI组件**: Tailwind CSS + shadcn/ui
- **图标**: Lucide React
- **图表**: Recharts
- **HTTP客户端**: Axios

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   后端API       │    │   MySQL数据库   │
│   (React)       │◄──►│   (Flask)       │◄──►│                 │
│                 │    │                 │    │  - 10NC_based   │
│ - 查询界面      │    │ - 数据查询API   │    │  - 12NC_based   │
│ - 结果展示      │    │ - AI分析API     │    │  - 12NC_based2  │
│ - 数据导出      │    │ - 导出API       │    │  - 其他表       │
│ - 智能对话      │    │ - 智能对话API   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │                 │
                       │ - GPT模型       │
                       │ - 自然语言处理  │
                       │ - 数据分析      │
                       └─────────────────┘
```

## 核心功能模块

### 1. 数据查询模块
- **功能**: 支持SQL查询和自然语言查询
- **实现**: 
  - 直接SQL查询执行
  - 自然语言转SQL（使用OpenAI API）
  - 查询结果分页和过滤

### 2. 智能分析模块
- **功能**: 数据智能分析和总结
- **实现**:
  - 数据统计分析
  - 趋势分析
  - 异常检测
  - 智能报告生成

### 3. 数据导出模块
- **功能**: 多格式数据导出
- **实现**:
  - CSV导出
  - Excel导出
  - PDF报告导出
  - JSON数据导出

### 4. 智能对话模块
- **功能**: 与AI助手对话查询数据
- **实现**:
  - 自然语言理解
  - 上下文记忆
  - 多轮对话支持

## API设计

### 数据查询API
```
GET /api/tables - 获取所有表列表
GET /api/tables/{table_name}/columns - 获取表结构
POST /api/query - 执行SQL查询
POST /api/nl_query - 自然语言查询
```

### AI分析API
```
POST /api/analyze - 数据分析
POST /api/summarize - 数据总结
POST /api/chat - 智能对话
```

### 数据导出API
```
POST /api/export/csv - CSV导出
POST /api/export/excel - Excel导出
POST /api/export/pdf - PDF导出
```

## 数据库设计

### 已迁移的表
1. **10NC_based** - 产品基础信息表 (24,329条记录)
2. **12NC_based** - 产品详细信息表
3. **12NC_based2** - 产品样品信息表
4. **12NCspec_based** - 产品规格信息表
5. **12NCspec_based2** - 产品扩展规格表
6. **12NCspec_based3** - 产品附加规格表

### 表关系
- 以10NC和12NC作为主要关联字段
- 支持多表联合查询和分析

## 安全考虑

1. **数据库安全**
   - 使用专用数据库用户
   - 限制数据库访问权限
   - SQL注入防护

2. **API安全**
   - 输入验证和清理
   - 查询限制和超时控制
   - 错误信息脱敏

3. **AI安全**
   - API密钥安全存储
   - 请求频率限制
   - 敏感数据过滤

## 部署方案

### 本地部署
1. MySQL服务运行在localhost:3306
2. Flask后端运行在0.0.0.0:5000
3. React前端构建后部署到Flask静态目录
4. 通过单一端口提供完整服务

### 配置要求
- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- 至少2GB内存
- 10GB存储空间

## 开发计划

1. **Phase 4**: 开发后端API服务
2. **Phase 5**: 开发前端界面
3. **Phase 6**: 集成AI功能和数据处理
4. **Phase 7**: 本地测试和调试
5. **Phase 8**: 部署和交付成果

