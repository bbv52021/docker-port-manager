"""
Docker Port Manager - 主入口
"""

import logging
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.api.routes import api_bp, init_api
from app.config import WEB_HOST, WEB_PORT, DATA_DIR

# 创建数据目录
os.makedirs(DATA_DIR, exist_ok=True)


def create_app():
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # CORS
    CORS(app)

    # 注册 API 蓝图
    app.register_blueprint(api_bp)

    # 初始化 API
    with app.app_context():
        init_api()

    # 首页路由
    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
