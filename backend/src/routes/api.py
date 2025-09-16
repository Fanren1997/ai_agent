from flask import Blueprint, request, jsonify, send_file
from src.database import db_manager
from src.services.ai_service import AIService
from src.services.export_service import ExportService
import json
import os
import tempfile

api_bp = Blueprint('api', __name__)
ai_service = AIService()
export_service = ExportService()

@api_bp.route('/tables', methods=['GET'])
def get_tables():
    """获取所有表列表"""
    try:
        tables = db_manager.get_tables()
        # 过滤掉系统表和空表名
        filtered_tables = [t for t in tables if t and not t.startswith('__')]
        
        table_info = []
        for table in filtered_tables:
            count = db_manager.get_table_count(table)
            table_info.append({
                'name': table,
                'count': count
            })
        
        return jsonify({
            'success': True,
            'data': table_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/tables/<table_name>/columns', methods=['GET'])
def get_table_columns(table_name):
    """获取表结构"""
    try:
        columns = db_manager.get_table_columns(table_name)
        return jsonify({
            'success': True,
            'data': columns
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/query', methods=['POST'])
def execute_query():
    """执行SQL查询"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询语句不能为空'
            }), 400
        
        # 安全检查：只允许SELECT查询
        if not query.upper().strip().startswith('SELECT'):
            return jsonify({
                'success': False,
                'error': '只允许SELECT查询'
            }), 400
        
        # 添加分页
        offset = (page - 1) * page_size
        paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
        
        # 执行查询
        result = db_manager.execute_query(paginated_query)
        
        # 获取总记录数（用于分页）
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as count_table"
        count_result = db_manager.execute_query(count_query)
        total = count_result[0]['total'] if count_result else 0
        
        return jsonify({
            'success': True,
            'data': {
                'rows': result or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nl_query', methods=['POST'])
def natural_language_query():
    """自然语言查询"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'error': '问题不能为空'
            }), 400
        
        # 使用AI服务将自然语言转换为SQL
        sql_query = ai_service.nl_to_sql(question)
        
        if not sql_query:
            return jsonify({
                'success': False,
                'error': 'AI服务暂时不可用'
            }), 500
        
        # 执行生成的SQL查询
        result = db_manager.execute_query(sql_query)
        
        return jsonify({
            'success': True,
            'data': {
                'sql': sql_query,
                'rows': result or [],
                'question': question
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/analyze', methods=['POST'])
def analyze_data():
    """数据分析"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        analysis_type = data.get('analysis_type', 'summary')
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询语句不能为空'
            }), 400
        
        # 执行查询获取数据
        result = db_manager.execute_query(query)
        
        if not result:
            return jsonify({
                'success': False,
                'error': '查询没有返回数据'
            }), 400
        
        # 使用AI服务分析数据
        analysis = ai_service.analyze_data(result, analysis_type)
        
        return jsonify({
            'success': True,
            'data': {
                'analysis': analysis,
                'row_count': len(result)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/chat', methods=['POST'])
def chat():
    """智能对话"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        context = data.get('context', [])
        
        if not message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        # 使用AI服务处理对话
        response = ai_service.chat(message, context)
        
        return jsonify({
            'success': True,
            'data': {
                'response': response,
                'message': message
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/export/csv', methods=['POST'])
def export_csv():
    """导出CSV"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        filename = data.get('filename', 'export.csv')
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询语句不能为空'
            }), 400
        
        # 执行查询
        result = db_manager.execute_query(query)
        
        if not result:
            return jsonify({
                'success': False,
                'error': '查询没有返回数据'
            }), 400
        
        # 生成CSV文件
        file_path = export_service.export_to_csv(result, filename)
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/export/excel', methods=['POST'])
def export_excel():
    """导出Excel"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        filename = data.get('filename', 'export.xlsx')
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询语句不能为空'
            }), 400
        
        # 执行查询
        result = db_manager.execute_query(query)
        
        if not result:
            return jsonify({
                'success': False,
                'error': '查询没有返回数据'
            }), 400
        
        # 生成Excel文件
        file_path = export_service.export_to_excel(result, filename)
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        tables = db_manager.get_tables()
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy',
                'database': 'connected',
                'tables_count': len(tables)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

