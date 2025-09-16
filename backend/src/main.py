import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.config import Config
from src.routes.api import api_bp
from src.routes.user import user_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config.from_object(Config)

# 启用CORS支持
CORS(app, origins="*")

# 注册蓝图
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api')

# 创建上传目录
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.errorhandler(404)
def not_found(error):
    return {"success": False, "error": "API endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"success": False, "error": "Internal server error"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

