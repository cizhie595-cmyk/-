"""
Coupang 选品系统 - Web API 服务器
基于 Flask 提供 RESTful API 接口

启动方式:
    python app.py                    # 开发模式 (debug)
    python app.py --port 8080        # 指定端口
    python app.py --host 0.0.0.0     # 允许外部访问
"""

import os
import sys
import argparse
from datetime import datetime

from flask import Flask, jsonify
from flask_cors import CORS

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.logger import get_logger

logger = get_logger()


def create_app() -> Flask:
    """
    Flask 应用工厂函数
    """
    app = Flask(__name__)

    # === 基础配置 ===
    app.config["JSON_AS_ASCII"] = False           # 支持中文/韩文 JSON 输出
    app.config["JSON_SORT_KEYS"] = False           # 保持 JSON 字段顺序
    app.config["SECRET_KEY"] = os.getenv(
        "FLASK_SECRET_KEY", "coupang-selection-flask-secret"
    )

    # === 跨域配置 ===
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # === 注册蓝图 (路由模块) ===
    from api.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # === 全局路由 ===

    @app.route("/")
    def index():
        """API 根路径 - 系统信息"""
        return jsonify({
            "system": "Coupang 跨境电商智能选品系统",
            "version": "1.0.0",
            "api_docs": "/api/docs",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
        })

    @app.route("/api/health")
    def health_check():
        """健康检查接口"""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
        })

    @app.route("/api/docs")
    def api_docs():
        """API 接口文档概览"""
        return jsonify({
            "auth": {
                "POST /api/auth/register": "用户注册",
                "POST /api/auth/login": "用户登录",
                "POST /api/auth/refresh": "刷新Token",
                "GET  /api/auth/me": "获取当前用户信息（需登录）",
                "PUT  /api/auth/me": "更新当前用户信息（需登录）",
                "POST /api/auth/change-password": "修改密码（需登录）",
                "GET  /api/auth/users": "用户列表（需管理员）",
                "PUT  /api/auth/users/<id>/status": "启用/禁用用户（需管理员）",
                "PUT  /api/auth/users/<id>/role": "设置用户角色（需管理员）",
            },
        })

    # === 全局错误处理 ===

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "error": "not_found",
            "message": "请求的接口不存在",
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "success": False,
            "error": "method_not_allowed",
            "message": "不支持的请求方法",
        }), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"服务器内部错误: {e}")
        return jsonify({
            "success": False,
            "error": "internal_error",
            "message": "服务器内部错误",
        }), 500

    return app


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coupang 选品系统 API 服务器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="监听端口 (默认: 5000)")
    parser.add_argument("--debug", action="store_true", help="开启调试模式")
    args = parser.parse_args()

    app = create_app()

    logger.info(f"Coupang 选品系统 API 服务器启动: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
