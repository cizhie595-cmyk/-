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

from flask import Flask, jsonify, send_from_directory, render_template
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
    # 前端文件目录
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    app = Flask(
        __name__,
        template_folder=os.path.join(frontend_dir, "templates"),
        static_folder=os.path.join(frontend_dir, "static"),
        static_url_path="/static",
    )

    # === 基础配置 ===
    app.config["JSON_AS_ASCII"] = False           # 支持中文/韩文 JSON 输出
    app.config["JSON_SORT_KEYS"] = False           # 保持 JSON 字段顺序
    app.config["SECRET_KEY"] = os.getenv(
        "FLASK_SECRET_KEY", "coupang-selection-flask-secret"
    )

    # === 生产环境安全检查 ===
    _unsafe_defaults = [
        "coupang-selection-flask-secret",
        "coupang-selection-system-secret-key-change-in-production",
        "your-random-secret-key-change-this-in-production",
        "your-flask-secret-key",
        "your-flask-secret-key-change-this-in-production",
    ]
    flask_env = os.getenv("FLASK_ENV", "development")
    if flask_env == "production":
        if app.config["SECRET_KEY"] in _unsafe_defaults:
            logger.warning(
                "[SECURITY] FLASK_SECRET_KEY 使用默认值！"
                "请在生产环境中设置安全的随机密钥。"
            )
        jwt_key = os.getenv("JWT_SECRET_KEY", "")
        if not jwt_key or jwt_key in _unsafe_defaults:
            logger.warning(
                "[SECURITY] JWT_SECRET_KEY 未配置或使用默认值！"
                "请在生产环境中设置安全的随机密钥。"
            )
        enc_key = os.getenv("API_KEYS_ENCRYPTION_KEY", "")
        if not enc_key or len(enc_key) < 32:
            logger.warning(
                "[SECURITY] API_KEYS_ENCRYPTION_KEY 未配置或长度不足！"
                "请配置 64 位十六进制字符串以启用 AES-256-GCM 加密。"
            )

    # === 跨域配置 ===
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # === API 限流中间件 ===
    try:
        from auth.rate_limiter import init_rate_limiter
        limiter = init_rate_limiter(app)
        if limiter:
            app.extensions["limiter"] = limiter
            logger.info("[App] API 限流中间件已启用")
    except Exception as rl_err:
        logger.warning(f"API 限流初始化失败 (非必要): {rl_err}")

    # === 注册蓝图 (路由模块) ===
    from api.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    from api.ai_config_routes import ai_config_bp
    app.register_blueprint(ai_config_bp)

    from api.api_keys_routes import api_keys_bp
    app.register_blueprint(api_keys_bp)

    from api.monetization_routes import monetization_bp
    app.register_blueprint(monetization_bp)

    from api.project_routes import project_bp
    app.register_blueprint(project_bp)

    from api.analysis_routes import analysis_bp
    app.register_blueprint(analysis_bp)

    from api.threed_routes import threed_bp
    app.register_blueprint(threed_bp)

    from api.profit_routes import profit_bp
    app.register_blueprint(profit_bp)

    from api.upload_routes import upload_bp
    app.register_blueprint(upload_bp)

    from api.asset_download_routes import asset_download_bp
    app.register_blueprint(asset_download_bp)

    from api.dashboard_routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # === WebSocket (Chrome 插件通信) ===
    try:
        from api.websocket_handler import register_websocket_routes
        register_websocket_routes(app)
    except Exception as ws_err:
        logger.warning(f"WebSocket 初始化失败 (非必要): {ws_err}")

    # === 前端页面路由 ===
    from frontend.routes import frontend_bp
    app.register_blueprint(frontend_bp)

    # PRD 8.1: /api/v1/user/quota 别名路由
    @app.route("/api/v1/user/quota")
    def user_quota_alias():
        """PRD 8.1 兼容路由 -> 转发到 /api/auth/quota"""
        from api.auth_routes import get_user_quota
        from auth.middleware import login_required
        # 手动调用 login_required 逻辑
        from auth.jwt_handler import verify_access_token
        from flask import request as req
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "未提供认证令牌"}), 401
        token = auth_header.split(" ", 1)[1]
        payload = verify_access_token(token)
        if not payload:
            return jsonify({"success": False, "message": "令牌无效或已过期"}), 401
        return get_user_quota(payload)

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
                "GET  /api/auth/quota": "获取用户额度信息（需登录）",
                "GET  /api/v1/user/quota": "获取用户额度信息 - PRD别名（需登录）",
                "PUT  /api/auth/me": "更新当前用户信息（需登录）",
                "POST /api/auth/change-password": "修改密码（需登录）",
                "GET  /api/auth/users": "用户列表（需管理员）",
                "PUT  /api/auth/users/<id>/status": "启用/禁用用户（需管理员）",
                "PUT  /api/auth/users/<id>/role": "设置用户角色（需管理员）",
            },
            "ai_config": {
                "GET  /api/ai/providers": "获取支持的AI服务商列表",
                "GET  /api/ai/settings": "获取当前用户的AI配置（需登录）",
                "POST /api/ai/settings": "保存/更新AI配置（需登录）",
                "POST /api/ai/test": "测试已保存的AI配置连通性（需登录）",
                "POST /api/ai/test-direct": "直接测试AI配置（不保存，需登录）",
            },
            "api_keys": {
                "GET  /api/keys/services": "获取支持的第三方服务列表",
                "GET  /api/keys/all": "获取所有服务的脱敏配置（需登录）",
                "GET  /api/keys/<service_id>": "获取某服务的脱敏配置（需登录）",
                "POST /api/keys/<service_id>": "保存某服务的配置（需登录）",
                "POST /api/keys/<service_id>/test": "测试某服务的连通性（需登录）",
                "DELETE /api/keys/<service_id>": "删除某服务的配置（需登录）",
            },
            "subscription": {
                "GET  /api/subscription/plans": "获取所有订阅计划",
                "GET  /api/subscription/me": "获取当前用户订阅状态（需登录）",
                "POST /api/subscription/upgrade": "升级订阅（需登录）",
                "POST /api/subscription/cancel": "取消订阅（需登录）",
                "GET  /api/subscription/usage": "获取使用量统计（需登录）",
                "POST /api/affiliate/link": "生成 Affiliate 链接（需登录）",
                "POST /api/affiliate/batch": "批量生成 Affiliate 链接（需登录）",
            },
            "projects": {
                "POST /api/v1/projects": "创建选品项目",
                "GET  /api/v1/projects": "获取项目列表",
                "GET  /api/v1/projects/<id>": "获取项目详情",
                "PUT  /api/v1/projects/<id>": "更新项目",
                "DELETE /api/v1/projects/<id>": "删除项目",
                "POST /api/v1/projects/<id>/run": "执行项目抓取",
            },
            "analysis": {
                "POST /api/v1/analysis/visual": "发起视觉语义分析",
                "POST /api/v1/analysis/reviews": "发起评论深度挖掘",
                "GET  /api/v1/analysis/<task_id>/result": "获取分析结果",
                "POST /api/v1/analysis/report/generate": "生成综合决策报告",
            },
            "3d_assets": {
                "POST /api/v1/3d/generate": "发起 2D 转 3D 任务",
                "GET  /api/v1/3d/<asset_id>/status": "轮询 3D 生成进度",
                "POST /api/v1/3d/<asset_id>/render-video": "发起视频渲染",
                "GET  /api/v1/3d/<asset_id>/video": "获取渲染视频",
                "GET  /api/v1/3d/assets": "获取 3D 资产列表",
            },
            "dashboard": {
                "GET  /api/v1/dashboard/stats": "获取仪表盘统计数据（需登录）",
                "GET  /api/v1/dashboard/activity-chart": "获取最近7天活动图表数据（需登录）",
            },
            "profit_supply": {
                "POST /api/v1/profit/calculate": "计算单品利润",
                "POST /api/v1/profit/batch": "批量利润计算",
                "POST /api/v1/supply/image-search": "以图搜货 (1688)",
                "POST /api/v1/supply/keyword-search": "关键词搜货 (1688)",
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
