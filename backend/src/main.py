# -*- coding: utf-8 -*-
"""
AI Agent 后端入口 (一键启动)
自动加载虚拟环境 + 环境变量 + 同步 Access 数据 + 启动 Flask 服务
兼容 Windows GBK 控制台，不使用 emoji。
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# ==========================================================
# Step 1. 修正路径 & 自动加载虚拟环境
# ==========================================================
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[1]
PROJECT_ROOT = CURRENT_FILE.parents[2]   # system/
SRC_DIR = BACKEND_DIR / "src"

# 保证 backend/src 可导入
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 自动加载虚拟环境 site-packages
VENV_SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))
    print(f"[OK] 已加载虚拟环境依赖: {VENV_SITE}")
else:
    print("[WARN] 未找到虚拟环境，将使用系统 Python 环境。")

# ==========================================================
# Step 2. 自动加载 .env 文件
# ==========================================================
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"[OK] 已加载环境变量文件: {ENV_PATH}")
else:
    print("[WARN] 未找到 .env 文件，请检查路径。")

# ==========================================================
# Step 3. 自动同步 Access → MySQL
# ==========================================================
def sync_access_to_mysql():
    """
    调用 data_sync/access_mysql_sync_tool.py 自动执行同步
    """
    sync_tool = PROJECT_ROOT / "data_sync" / "access_mysql_sync_tool.py"
    if not sync_tool.exists():
        print(f"[ERROR] 未找到同步脚本: {sync_tool}")
        return False

    print("[INFO] 开始执行 Access → MySQL 同步 ...")
    try:
        result = subprocess.run(
            [sys.executable, str(sync_tool)],
            cwd=str(sync_tool.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        print("[SYNC OUTPUT]")
        print(result.stdout)
        if result.returncode == 0:
            print("[OK] 数据同步完成。")
            return True
        else:
            print("[WARN] 同步失败:")
            print(result.stderr)
            return False
    except Exception as e:
        print("[ERROR] 同步异常:", e)
        return False

# ==========================================================
# Step 4. 启动 Flask 后端
# ==========================================================
from flask import Flask
from flask_cors import CORS

try:
    from src.routes.api import api_bp
except ModuleNotFoundError:
    sys.path.append(str(SRC_DIR))
    from src.routes.api import api_bp


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return "Backend is running (Access Sync + DeepSeek)."

    return app

# ==========================================================
# Step 5. 主入口
# ==========================================================
if __name__ == "__main__":
    print("\n[START] AI Agent 后端启动中...\n")

    # 1️⃣ 自动同步 Access 数据
    sync_access_to_mysql()

    # 2️⃣ 启动 Flask
    app = create_app()
    print("\n[INFO] 访问地址: http://127.0.0.1:5000")
    print("[INFO] API 接口: /api/health /api/chat")
    print("[INFO] 系统已启动，请保持此窗口开启。\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
