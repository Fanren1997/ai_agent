# -*- coding: utf-8 -*-
"""
主入口 · 自动激活虚拟环境 + 同步 Access 数据 + 启动 Flask 后端
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# === 1️⃣ 自动激活虚拟环境 ==============================================
VENV_PATH = Path(__file__).resolve().parents[2] / ".venv" / "Lib" / "site-packages"
if str(VENV_PATH) not in sys.path and VENV_PATH.exists():
    sys.path.insert(0, str(VENV_PATH))
    print(f"✅ 已加载虚拟环境依赖: {VENV_PATH}")
else:
    print("⚠️ 未找到虚拟环境，继续使用全局 Python 环境。")

# === 2️⃣ 自动加载 .env 配置 ==============================================
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"✅ 已加载环境变量文件: {ENV_PATH}")
else:
    print("⚠️ 未找到 .env 文件，请确认路径正确。")

# === 3️⃣ 自动执行 Access → MySQL 同步 ===================================
def sync_access_to_mysql():
    """
    调用 data_sync/access_mysql_sync_tool.py 自动同步 Access → MySQL
    """
    sync_tool = ROOT_DIR / "data_sync" / "access_mysql_sync_tool.py"
    if not sync_tool.exists():
        print(f"❌ 未找到同步脚本: {sync_tool}")
        return False

    print("🔄 正在执行 Access → MySQL 同步 ...")
    try:
        result = subprocess.run(
            ["python", str(sync_tool)],
            cwd=str(sync_tool.parent),
            capture_output=True,
            text=True,
        )
        print("🪄 同步输出:\n", result.stdout)
        if result.returncode == 0:
            print("✅ 数据同步完成。")
            return True
        else:
            print("⚠️ 同步失败:\n", result.stderr)
            return False
    except Exception as e:
        print("❌ 同步异常:", e)
        return False


# === 4️⃣ 启动 Flask 服务 ==============================================
from flask import Flask
from flask_cors import CORS

# 导入你的 API 蓝图
from src.routes.api import api_bp


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    CORS(app)

    # 注册路由蓝图
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return "Backend is running (with Access sync + DeepSeek)."

    return app


# === 5️⃣ 主执行逻辑 =====================================================
if __name__ == "__main__":
    # Step 1: 同步 Access → MySQL 数据
    sync_access_to_mysql()

    # Step 2: 启动 Flask
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
