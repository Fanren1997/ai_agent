# backend/src/main.py
# —— 确保无论从哪启动，都能找到 src 包（把 backend 加入 sys.path）——
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../backend
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from flask_cors import CORS
from src.routes.api import api_bp

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return "Backend is running."
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
