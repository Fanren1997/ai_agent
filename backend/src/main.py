# backend/src/main.py
import os
import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# =========================================================
# 🔹 Step 1. 自动加载虚拟环境 site-packages
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # system 根目录
VENV_SITE_PACKAGES = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"

if VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))
    print(f"✅ 已加载虚拟环境依赖: {VENV_SITE_PACKAGES}")
else:
    print("⚠️ 未找到虚拟环境 site-packages，使用全局环境。")

# =========================================================
# 🔹 Step 2. 自动加载 .env 文件
# =========================================================
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"✅ 已加载环境变量文件: {ENV_PATH}")
else:
    print("⚠️ 未找到 .env 文件，请确认路径是否正确。")

# =========================================================
# 🔹 Step 3. 导入路径配置
# =========================================================
SRC_PATH = Path(__file__).resolve().parents[1]  # backend/src
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# =========================================================
# 🔹 Step 4. 导入路由模块
# =========================================================
from src.routes.api import api_bp


def create_app() -> Flask:
    """创建 Flask 应用实例"""
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return "✅ Backend is running. Try /api/health"

    return app


# =========================================================
# 🔹 Step 5. 启动 Flask 服务
# =========================================================
app = create_app()

if __name__ == "__main__":
    print("\n🚀 Flask Backend 启动中...")
    print("🌐 地址: http://127.0.0.1:5000")
    print("📡 可用接口: /api/chat, /api/health")
    print("⚙️ 请保持此窗口打开。\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
