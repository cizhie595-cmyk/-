"""
Coupang 选品系统 - 认证中间件
提供: Flask/FastAPI 路由保护装饰器
"""

from functools import wraps
from flask import request, jsonify, g

from auth.jwt_handler import verify_access_token
from utils.logger import get_logger

logger = get_logger()


def login_required(f):
    """
    登录验证装饰器
    从请求头 Authorization: Bearer <token> 中提取并验证 JWT

    用法:
        @app.route("/api/protected")
        @login_required
        def protected_route():
            user = g.current_user  # 获取当前登录用户信息
            return jsonify({"user_id": user["user_id"]})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({
                "success": False,
                "error": "missing_token",
                "message": "请先登录（缺少认证令牌）",
            }), 401

        user_info = verify_access_token(token)
        if not user_info:
            return jsonify({
                "success": False,
                "error": "invalid_token",
                "message": "认证令牌无效或已过期，请重新登录",
            }), 401

        # 将用户信息存入 Flask 的 g 对象，供后续使用
        g.current_user = user_info
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    管理员权限验证装饰器
    需要用户已登录且角色为 admin

    用法:
        @app.route("/api/admin/users")
        @admin_required
        def admin_users():
            return jsonify({"users": [...]})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({
                "success": False,
                "error": "missing_token",
                "message": "请先登录",
            }), 401

        user_info = verify_access_token(token)
        if not user_info:
            return jsonify({
                "success": False,
                "error": "invalid_token",
                "message": "认证令牌无效或已过期",
            }), 401

        if user_info.get("role") != "admin":
            return jsonify({
                "success": False,
                "error": "forbidden",
                "message": "权限不足，需要管理员权限",
            }), 403

        g.current_user = user_info
        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """
    角色权限验证装饰器（支持多角色）

    用法:
        @app.route("/api/reports")
        @role_required("admin", "user")
        def get_reports():
            return jsonify({"reports": [...]})
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = _extract_token()
            if not token:
                return jsonify({
                    "success": False,
                    "error": "missing_token",
                    "message": "请先登录",
                }), 401

            user_info = verify_access_token(token)
            if not user_info:
                return jsonify({
                    "success": False,
                    "error": "invalid_token",
                    "message": "认证令牌无效或已过期",
                }), 401

            if user_info.get("role") not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": "forbidden",
                    "message": f"权限不足，需要以下角色之一: {', '.join(allowed_roles)}",
                }), 403

            g.current_user = user_info
            return f(*args, **kwargs)

        return decorated
    return decorator


def _extract_token() -> str | None:
    """
    从请求中提取 JWT Token

    支持两种方式:
    1. Authorization: Bearer <token>  (推荐)
    2. URL 参数: ?token=<token>       (备用)
    """
    # 方式1: 从 Authorization 头提取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # 方式2: 从 URL 参数提取
    token = request.args.get("token")
    if token:
        return token

    return None
