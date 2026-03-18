"""
Coupang 选品系统 - OAuth 第三方登录 API 路由
提供: Google/GitHub OAuth 登录流程
"""

import os
import secrets
from flask import Blueprint, request, jsonify, redirect, session
from auth.oauth_handler import (
    OAuthProvider, get_oauth_auth_url, oauth_callback,
)
from auth.jwt_handler import create_access_token
from utils.logger import get_logger

logger = get_logger()

oauth_bp = Blueprint("oauth", __name__, url_prefix="/api/oauth")

APP_FRONTEND_URL = os.getenv("APP_FRONTEND_URL", "http://localhost:5000")


# ============================================================
# GET /api/oauth/providers - 获取可用的 OAuth 提供商
# ============================================================
@oauth_bp.route("/providers", methods=["GET"])
def get_providers():
    """获取已配置的 OAuth 提供商列表"""
    return jsonify({
        "success": True,
        "providers": OAuthProvider.get_available_providers(),
    }), 200


# ============================================================
# GET /api/oauth/<provider>/authorize - 发起 OAuth 授权
# ============================================================
@oauth_bp.route("/<provider>/authorize", methods=["GET"])
def authorize(provider):
    """
    发起 OAuth 授权，重定向到第三方登录页面

    支持的 provider: google, github
    """
    if provider not in ("google", "github"):
        return jsonify({"success": False, "message": "不支持的登录方式"}), 400

    if not OAuthProvider.is_configured(provider):
        return jsonify({
            "success": False,
            "message": f"{provider} 登录未配置，请联系管理员",
        }), 503

    # 生成 CSRF state
    state = secrets.token_urlsafe(32)
    session[f"oauth_state_{provider}"] = state

    auth_url = get_oauth_auth_url(provider, state)
    if not auth_url:
        return jsonify({"success": False, "message": "生成授权链接失败"}), 500

    return jsonify({
        "success": True,
        "auth_url": auth_url,
    }), 200


# ============================================================
# GET /api/oauth/<provider>/callback - OAuth 回调
# ============================================================
@oauth_bp.route("/<provider>/callback", methods=["GET"])
def callback(provider):
    """
    OAuth 回调端点

    处理第三方授权码，获取用户信息，创建/关联账户，返回 JWT
    """
    if provider not in ("google", "github"):
        return jsonify({"success": False, "message": "不支持的登录方式"}), 400

    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        logger.warning(f"[OAuth] {provider} 授权失败: {error}")
        return redirect(f"{APP_FRONTEND_URL}/login?error=oauth_denied")

    if not code:
        return redirect(f"{APP_FRONTEND_URL}/login?error=no_code")

    # 验证 state（CSRF 防护）
    expected_state = session.pop(f"oauth_state_{provider}", None)
    if expected_state and state != expected_state:
        logger.warning(f"[OAuth] State mismatch: expected={expected_state}, got={state}")
        return redirect(f"{APP_FRONTEND_URL}/login?error=invalid_state")

    # 获取用户信息
    user_info = oauth_callback(provider, code)
    if not user_info:
        logger.error(f"[OAuth] {provider} 获取用户信息失败")
        return redirect(f"{APP_FRONTEND_URL}/login?error=oauth_failed")

    # 查找或创建用户
    try:
        user, is_new = _find_or_create_oauth_user(user_info)
    except Exception as e:
        logger.error(f"[OAuth] 用户处理失败: {e}")
        return redirect(f"{APP_FRONTEND_URL}/login?error=server_error")

    # 生成 JWT
    token = create_access_token(
        user_id=user["id"],
        username=user.get("username", ""),
        role=user.get("role", "user"),
    )

    # 记录审计日志
    try:
        from utils.audit_logger import audit, AuditLogger
        audit.log(
            action=AuditLogger.ACTION_LOGIN,
            user_id=user["id"],
            details={"method": f"oauth_{provider}", "is_new_user": is_new},
        )
    except Exception:
        pass

    # 重定向到前端并携带 token
    return redirect(f"{APP_FRONTEND_URL}/oauth/callback?token={token}&provider={provider}&new={int(is_new)}")


def _find_or_create_oauth_user(user_info: dict) -> tuple:
    """
    查找或创建 OAuth 用户

    :param user_info: OAuth 提供商返回的用户信息
    :return: (user_dict, is_new_user)
    """
    from database.connection import db

    provider = user_info["provider"]
    provider_id = user_info["provider_id"]
    email = user_info.get("email")

    # 1. 先查找 OAuth 绑定记录
    oauth_record = db.fetch_one(
        "SELECT * FROM user_oauth WHERE provider = %s AND provider_id = %s",
        (provider, provider_id),
    )

    if oauth_record:
        # 已绑定，获取用户信息
        user = db.fetch_one(
            "SELECT id, username, email, role FROM users WHERE id = %s",
            (oauth_record["user_id"],),
        )
        if user:
            return user, False

    # 2. 通过邮箱查找已有用户
    if email:
        existing_user = db.fetch_one(
            "SELECT id, username, email, role FROM users WHERE email = %s",
            (email,),
        )
        if existing_user:
            # 绑定 OAuth 到已有账户
            db.execute(
                """INSERT INTO user_oauth (user_id, provider, provider_id, provider_name, provider_avatar)
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE provider_name = VALUES(provider_name)""",
                (existing_user["id"], provider, provider_id,
                 user_info.get("name", ""), user_info.get("avatar", "")),
            )
            return existing_user, False

    # 3. 创建新用户
    username = _generate_unique_username(user_info.get("name", "user"), provider)

    user_id = db.insert_and_get_id(
        """INSERT INTO users (username, email, email_verified, role, created_at)
           VALUES (%s, %s, %s, 'user', NOW())""",
        (username, email, 1 if user_info.get("email_verified") else 0),
    )

    # 创建 OAuth 绑定
    db.execute(
        """INSERT INTO user_oauth (user_id, provider, provider_id, provider_name, provider_avatar)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, provider, provider_id,
         user_info.get("name", ""), user_info.get("avatar", "")),
    )

    new_user = {
        "id": user_id,
        "username": username,
        "email": email,
        "role": "user",
    }
    return new_user, True


def _generate_unique_username(name: str, provider: str) -> str:
    """生成唯一用户名"""
    from database.connection import db
    import re

    # 清理名称
    base = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))[:20]
    if not base:
        base = f"{provider}_user"

    username = base
    counter = 1
    while True:
        existing = db.fetch_one(
            "SELECT id FROM users WHERE username = %s", (username,)
        )
        if not existing:
            return username
        username = f"{base}_{counter}"
        counter += 1
