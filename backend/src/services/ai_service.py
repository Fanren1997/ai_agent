import openai
import json
from src.config import Config
from src.database import db_manager

class AIService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_API_BASE
        )
        self.model = "gpt-3.5-turbo"
    
    def get_database_schema(self):
        """获取数据库结构信息"""
        tables = db_manager.get_tables()
        schema_info = {}
        
        for table in tables:
            if table and not table.startswith('__'):
                columns = db_manager.get_table_columns(table)
                schema_info[table] = [
                    {
                        'name': col['Field'],
                        'type': col['Type'],
                        'null': col['Null'],
                        'key': col['Key']
                    } for col in columns
                ]
        
        return schema_info
    
    def nl_to_sql(self, question):
        """将自然语言转换为SQL查询"""
        try:
            schema = self.get_database_schema()
            
            system_prompt = f"""
你是一个SQL专家。根据用户的自然语言问题，生成相应的SQL查询语句。

数据库结构信息：
{json.dumps(schema, ensure_ascii=False, indent=2)}

规则：
1. 只生成SELECT查询语句
2. 使用反引号包围表名和列名
3. 确保SQL语法正确
4. 只返回SQL语句，不要其他解释
5. 如果问题不清楚，生成一个合理的查询

示例表说明：
- 10NC_based: 产品基础信息表
- 12NC_based: 产品详细信息表  
- 12NC_based2: 产品样品信息表
- 12NCspec_based: 产品规格信息表
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # 清理SQL查询，移除可能的代码块标记
            if sql_query.startswith('```sql'):
                sql_query = sql_query[6:]
            if sql_query.startswith('```'):
                sql_query = sql_query[3:]
            if sql_query.endswith('```'):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            print(f"NL to SQL 转换错误: {e}")
            return None
    
    def analyze_data(self, data, analysis_type='summary'):
        """分析数据并生成报告"""
        try:
            if not data:
                return "没有数据可供分析"
            
            # 限制数据量，避免token过多
            sample_data = data[:100] if len(data) > 100 else data
            
            system_prompt = f"""
你是一个数据分析专家。根据提供的数据进行{analysis_type}分析。

分析类型说明：
- summary: 数据摘要和基本统计
- trend: 趋势分析
- anomaly: 异常检测
- insight: 深入洞察

请用中文回答，提供清晰的分析结果。
"""
            
            user_prompt = f"""
请分析以下数据：

数据记录数：{len(data)}
样本数据：
{json.dumps(sample_data, ensure_ascii=False, indent=2)}

请进行{analysis_type}分析。
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"数据分析错误: {e}")
            return f"分析过程中出现错误: {str(e)}"
    
    def chat(self, message, context=None):
        """智能对话"""
        try:
            schema = self.get_database_schema()
            
            system_prompt = f"""
你是一个智能数据助手，可以帮助用户查询和分析数据库中的信息。

数据库结构：
{json.dumps(schema, ensure_ascii=False, indent=2)}

你可以：
1. 回答关于数据的问题
2. 帮助生成SQL查询
3. 解释数据含义
4. 提供数据分析建议

请用中文回答，保持友好和专业。
"""
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # 添加历史对话上下文
            if context:
                messages.extend(context[-10:])  # 只保留最近10轮对话
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"对话处理错误: {e}")
            return f"对话处理出现错误: {str(e)}"

