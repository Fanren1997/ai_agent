"""
Backend entrypoint: load config, start background sync, and serve Flask APIs.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# If console output needs UTF-8, uncomment next line to avoid garbled logs.
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[1]  # backend
PROJECT_ROOT = CURRENT_FILE.parents[2]  # project root (system)
SRC_DIR = BACKEND_DIR / "src"

for path in (BACKEND_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Optionally include .venv/site-packages
VENV_SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))
    print(f"[OK] 已加载虚拟环境依赖: {VENV_SITE}")
else:
    print("[WARN] 未找到虚拟环境，将使用系统 Python 环境")

# Load environment variables if available
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"[OK] 已加载环境变量文件: {ENV_PATH}")
else:
    print("[WARN] 未找到 .env 文件，请检查路径")


def sync_access_to_mysql_background() -> None:
    """Launch Access -> MySQL sync script in a background thread."""
    from src.services.sync_service import start_sync

    result = start_sync(stream_output=True)
    if result.get("ok"):
        print("\n[START] Access -> MySQL 异步同步启动...")
        print("[INFO] 异步同步任务已启动（后台执行，不阻塞 Flask）")
    else:
        print(f"[WARN] 同步任务未启动: {result.get('message')}")


def create_app() -> Flask:
    """Create Flask application and register blueprints."""
    static_path = str(BACKEND_DIR / "static")
    app = Flask(__name__, static_folder=static_path, static_url_path="/static")

    from src.routes.api import api_bp
    from src.routes.schema_api import schema_bp

    CORS(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(schema_bp)

    @app.route("/")
    def index():
        return """
        <h2>🤖 AI Agent Backend Running</h2>
        <p>✅ Flask + DeepSeek + Access Sync 已启动</p>
        <ul>
          <li><a href="/api/health">健康检查接口 /api/health</a></li>
          <li><a href="/static/schema_manager.html" target="_blank">Schema 管理页面</a></li>
        </ul>
        """

    return app


if __name__ == "__main__":
    print("\n[START] AI Agent 后端启动中..\n")
    sync_access_to_mysql_background()
    app = create_app()
    print("\n[INFO] 服务已启动")
    print("[INFO] 本地访问地址: http://127.0.0.1:5000")
    print("[INFO] Schema 管理页面: http://127.0.0.1:5000/static/schema_manager.html")
    print("[INFO] API 接口: /api/health /api/chat /api/schema/*\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
