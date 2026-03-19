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

    # === 静态文件缓存配置 (PRD NFR-01: 首屏性能优化) ===
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000  # 1 year for hashed assets

    @app.after_request
    def add_performance_headers(response):
        """PRD NFR-01: 添加缓存、压缩和安全头"""
        path = response.headers.get('X-Request-Path', '') or ''

        # Static file caching
        if '/static/' in str(getattr(response, 'headers', {}).get('Content-Type', '')):
            pass  # Use SEND_FILE_MAX_AGE_DEFAULT

        # Cache control for static assets
        content_type = response.headers.get('Content-Type', '')
        if any(ext in content_type for ext in ['css', 'javascript', 'font', 'image/svg', 'image/png', 'image/jpeg', 'image/webp']):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif 'text/html' in content_type:
            response.headers['Cache-Control'] = 'no-cache, must-revalidate'

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Vary header for proper CDN caching
        if 'Vary' not in response.headers:
            response.headers['Vary'] = 'Accept-Encoding'

        return response

    # === Gzip 压缩中间件 (PRD NFR-01) ===
    try:
        from flask_compress import Compress
        compress = Compress()
        compress.init_app(app)
        app.config['COMPRESS_MIMETYPES'] = [
            'text/html', 'text/css', 'text/javascript',
            'application/javascript', 'application/json',
            'image/svg+xml'
        ]
        app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses > 500 bytes
        app.config['COMPRESS_LEVEL'] = 6
        logger.info("[App] Gzip 压缩中间件已启用")
    except ImportError:
        logger.info("[App] flask-compress 未安装，跳过 Gzip 压缩")

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

    # Stripe 支付路由
    from api.stripe_routes import stripe_bp
    app.register_blueprint(stripe_bp)

    # 审计日志路由
    from api.audit_routes import audit_bp
    app.register_blueprint(audit_bp)

    # SSE 任务状态推送路由
    from api.sse_routes import sse_bp
    app.register_blueprint(sse_bp)

    # OAuth 第三方登录路由
    from api.oauth_routes import oauth_bp
    app.register_blueprint(oauth_bp)

    # 数据导出路由
    from api.export_routes import export_bp
    app.register_blueprint(export_bp)

    # 团队协作路由
    from api.team_routes import team_bp
    app.register_blueprint(team_bp)

    # 通知系统路由
    from api.notification_routes import notification_bp
    app.register_blueprint(notification_bp)

    # 数据清理与归档路由
    from api.cleanup_routes import cleanup_bp
    app.register_blueprint(cleanup_bp)

    # API 文档 (Swagger UI)
    from api.swagger_routes import swagger_bp
    app.register_blueprint(swagger_bp)

    # 前端国际化 API
    from api.i18n_routes import i18n_bp
    app.register_blueprint(i18n_bp)

    # APM 性能监控
    from api.apm_routes import apm_bp
    app.register_blueprint(apm_bp)
    from utils.apm_monitor import init_apm
    init_apm(app)

    # 竞品监控路由
    from api.competitor_routes import competitor_bp
    app.register_blueprint(competitor_bp)

    # 关键词研究路由
    from api.keyword_routes import keyword_bp
    app.register_blueprint(keyword_bp)

    # 供应商评分路由
    from api.supplier_routes import supplier_bp
    app.register_blueprint(supplier_bp)

    # 定价策略优化路由
    from api.pricing_routes import pricing_bp
    app.register_blueprint(pricing_bp)

    # 产品洞察路由 (BSR追踪/竞品发现/情感分析/AI决策/看板增强)
    from api.product_insight_routes import product_insight_bp
    app.register_blueprint(product_insight_bp)

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

    @app.route("/robots.txt")
    def robots_txt():
        """robots.txt"""
        return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')

    @app.route("/favicon.svg")
    def favicon_svg():
        """SVG Favicon"""
        return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')

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
    from utils.error_handler import register_error_handlers
    register_error_handlers(app)

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
