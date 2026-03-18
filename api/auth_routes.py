"""
Coupang 选品系统 - 用户认证 API 路由
提供: 注册、登录、Token刷新、登出、邮箱验证、密码重置 等接口
"""

from flask import Blueprint, request, jsonify, g

from auth.user_model import UserModel
from auth.password import (
    validate_password_strength,
    validate_email,
    validate_username,
)
from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    refresh_access_token,
    create_email_verification_token,
    create_password_reset_token,
    verify_email_verification_token,
    verify_password_reset_token,
)
from utils.email_sender import send_verification_email, send_password_reset_email
from auth.middleware import login_required, admin_required
from utils.logger import get_logger

logger = get_logger()

# 创建 Blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ============================================================
# POST /api/auth/register - 用户注册
# ============================================================
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    用户注册

    请求体 (JSON):
    {
        "username": "myuser",
        "email": "user@example.com",
        "password": "MyPass123",
        "nickname": "我的昵称",     // 可选
        "language": "zh_CN"         // 可选，默认 zh_CN
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    nickname = data.get("nickname", "").strip() or None
    language = data.get("language", "zh_CN")

    # === 参数验证 ===

    # 验证用户名
    if not username:
        return jsonify({"success": False, "message": "用户名不能为空"}), 400
    valid, msg = validate_username(username)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    # 验证邮箱
    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

    # 验证密码强度
    if not password:
        return jsonify({"success": False, "message": "密码不能为空"}), 400
    valid, msg = validate_password_strength(password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    # === 检查唯一性 ===
    exists = UserModel.check_exists(username=username, email=email)
    if exists["username_exists"]:
        return jsonify({"success": False, "message": "用户名已被注册"}), 409
    if exists["email_exists"]:
        return jsonify({"success": False, "message": "邮箱已被注册"}), 409

    # === 创建用户 ===
    user_id = UserModel.create(
        username=username,
        email=email,
        password=password,
        nickname=nickname,
        language=language,
    )

    if not user_id:
        return jsonify({"success": False, "message": "注册失败，请稍后重试"}), 500

    # 自动生成 Token（注册后自动登录）
    access_token = create_access_token(user_id, username, "user")
    refresh_token = create_refresh_token(user_id)

    logger.info(f"新用户注册: {username} ({email})")

    # 发送邮箱验证邮件
    try:
        verify_token = create_email_verification_token(user_id, email)
        send_verification_email(email, username, verify_token, language)
    except Exception as e:
        logger.warning(f"验证邮件发送失败: {e}")

    return jsonify({
        "success": True,
        "message": "注册成功，请查收验证邮件",
        "data": {
            "user_id": user_id,
            "username": username,
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "email_verified": False,
        }
    }), 201


# ============================================================
# POST /api/auth/login - 用户登录
# ============================================================
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录

    请求体 (JSON):
    {
        "login_id": "myuser 或 user@example.com",
        "password": "MyPass123"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    login_id = data.get("login_id", "").strip()
    password = data.get("password", "")

    if not login_id or not password:
        return jsonify({"success": False, "message": "用户名/邮箱和密码不能为空"}), 400

    # === 验证登录 ===
    user = UserModel.authenticate(login_id, password)

    if not user:
        # 记录失败日志（尝试获取用户ID）
        existing = UserModel.get_by_username(login_id) or UserModel.get_by_email(login_id)
        if existing:
            UserModel.record_login(
                user_id=existing["id"],
                ip=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                status="failed",
                fail_reason="密码错误",
            )
        return jsonify({"success": False, "message": "用户名/邮箱或密码错误"}), 401

    # === 生成 Token ===
    access_token = create_access_token(user["id"], user["username"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    # 记录成功登录
    UserModel.record_login(
        user_id=user["id"],
        ip=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        status="success",
    )

    logger.info(f"用户登录成功: {user['username']}")

    return jsonify({
        "success": True,
        "message": "登录成功",
        "data": {
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "nickname": user.get("nickname"),
            "role": user["role"],
            "language": user.get("language", "zh_CN"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }
    }), 200


# ============================================================
# POST /api/auth/refresh - 刷新 Token
# ============================================================
@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    刷新访问令牌

    请求体 (JSON):
    {
        "refresh_token": "eyJ..."
    }
    """
    data = request.get_json()
    if not data or not data.get("refresh_token"):
        return jsonify({"success": False, "message": "缺少 refresh_token"}), 400

    ref_token = data["refresh_token"]
    user_id = verify_refresh_token(ref_token)

    if not user_id:
        return jsonify({"success": False, "message": "刷新令牌无效或已过期"}), 401

    # 获取用户最新信息
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "用户不存在或已被禁用"}), 401

    # 生成新的 Access Token
    new_access_token = create_access_token(user["id"], user["username"], user["role"])

    return jsonify({
        "success": True,
        "message": "Token 刷新成功",
        "data": {
            "access_token": new_access_token,
            "token_type": "Bearer",
        }
    }), 200


# ============================================================
# GET /api/auth/me - 获取当前用户信息
# ============================================================
@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """获取当前登录用户的详细信息"""
    user_id = g.current_user["user_id"]
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    # 排除敏感字段
    safe_fields = {
        "id", "username", "email", "nickname", "avatar_url", "phone",
        "role", "is_active", "is_verified", "language",
        "openai_model", "last_login_at", "login_count", "created_at",
    }
    safe_user = {k: v for k, v in user.items() if k in safe_fields}

    # 标记是否已配置各项密钥（不返回实际值）
    safe_user["has_openai_key"] = bool(user.get("openai_api_key"))
    safe_user["has_coupang_account"] = bool(user.get("coupang_seller_email"))
    safe_user["has_naver_api"] = bool(user.get("naver_client_id"))

    return jsonify({
        "success": True,
        "data": safe_user,
    }), 200


# ============================================================
# PUT /api/auth/me - 更新当前用户信息
# ============================================================
@auth_bp.route("/me", methods=["PUT"])
@login_required
def update_current_user():
    """
    更新当前用户信息

    请求体 (JSON):
    {
        "nickname": "新昵称",
        "phone": "13800138000",
        "language": "en_US",
        "openai_api_key": "sk-...",
        "openai_model": "gpt-4o",
        "coupang_seller_email": "seller@example.com",
        "coupang_seller_password": "...",
        "naver_client_id": "...",
        "naver_client_secret": "..."
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    user_id = g.current_user["user_id"]
    success = UserModel.update_profile(user_id, data)

    if success:
        return jsonify({"success": True, "message": "信息更新成功"}), 200
    else:
        return jsonify({"success": False, "message": "更新失败，请检查字段是否有效"}), 400


# ============================================================
# POST /api/auth/change-password - 修改密码
# ============================================================
@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """
    修改密码

    请求体 (JSON):
    {
        "old_password": "OldPass123",
        "new_password": "NewPass456"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"success": False, "message": "原密码和新密码不能为空"}), 400

    # 验证新密码强度
    valid, msg = validate_password_strength(new_password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    user_id = g.current_user["user_id"]
    success, message = UserModel.change_password(user_id, old_password, new_password)

    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 400


# ============================================================
# GET /api/auth/verify-email - 邮箱验证
# ============================================================
@auth_bp.route("/verify-email", methods=["GET"])
def verify_email():
    """
    验证邮箱
    通过 URL 参数 token 验证邮箱地址
    """
    token = request.args.get("token", "")
    if not token:
        return jsonify({"success": False, "message": "缺少验证 Token"}), 400

    result = verify_email_verification_token(token)
    if not result:
        return jsonify({"success": False, "message": "验证链接无效或已过期"}), 400

    user_id = result["user_id"]
    email = result["email"]

    # 更新验证状态
    success = UserModel.set_email_verified(user_id, email)
    if success:
        logger.info(f"邮箱验证成功: user_id={user_id}, email={email}")
        return jsonify({"success": True, "message": "邮箱验证成功"}), 200
    else:
        return jsonify({"success": False, "message": "验证失败，请重试"}), 400


# ============================================================
# POST /api/auth/resend-verification - 重新发送验证邮件
# ============================================================
@auth_bp.route("/resend-verification", methods=["POST"])
@login_required
def resend_verification():
    """
    重新发送邮箱验证邮件
    限制: 每个用户每小时最多 3 次
    """
    user_id = g.current_user["user_id"]
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    if user.get("is_verified"):
        return jsonify({"success": False, "message": "邮箱已验证，无需重复操作"}), 400

    # 生成新的验证 Token 并发送
    verify_token = create_email_verification_token(user_id, user["email"])
    sent = send_verification_email(
        user["email"], user["username"], verify_token,
        user.get("language", "zh_CN")
    )

    if sent:
        return jsonify({"success": True, "message": "验证邮件已发送，请查收"}), 200
    else:
        return jsonify({"success": False, "message": "邮件发送失败，请稍后重试"}), 500


# ============================================================
# POST /api/auth/forgot-password - 忘记密码
# ============================================================
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    忘记密码 - 发送密码重置邮件

    请求体 (JSON):
    {
        "email": "user@example.com"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    email = data.get("email", "").strip()
    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400

    # 无论用户是否存在，都返回相同的成功响应（防止邮箱枚举攻击）
    user = UserModel.get_by_email(email)
    if user:
        reset_token = create_password_reset_token(user["id"], email)
        send_password_reset_email(
            email, user["username"], reset_token,
            user.get("language", "zh_CN")
        )
        logger.info(f"密码重置邮件已发送: {email}")

    return jsonify({
        "success": True,
        "message": "如果该邮箱已注册，您将收到一封密码重置邮件"
    }), 200


# ============================================================
# POST /api/auth/reset-password - 重置密码
# ============================================================
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    重置密码

    请求体 (JSON):
    {
        "token": "eyJ...",
        "new_password": "NewPass456"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    token = data.get("token", "")
    new_password = data.get("new_password", "")

    if not token:
        return jsonify({"success": False, "message": "缺少重置 Token"}), 400
    if not new_password:
        return jsonify({"success": False, "message": "新密码不能为空"}), 400

    # 验证新密码强度
    valid, msg = validate_password_strength(new_password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    # 验证 Token
    result = verify_password_reset_token(token)
    if not result:
        return jsonify({"success": False, "message": "重置链接无效或已过期"}), 400

    user_id = result["user_id"]

    # 重置密码
    success = UserModel.reset_password(user_id, new_password)
    if success:
        logger.info(f"密码重置成功: user_id={user_id}")
        return jsonify({"success": True, "message": "密码重置成功，请使用新密码登录"}), 200
    else:
        return jsonify({"success": False, "message": "密码重置失败，请重试"}), 400


# ============================================================
# GET /api/auth/users - 管理员: 获取用户列表
# ============================================================
@auth_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """管理员查看用户列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    result = UserModel.list_users(page=page, page_size=page_size)

    return jsonify({
        "success": True,
        "data": result,
    }), 200


# ============================================================
# PUT /api/auth/users/<user_id>/status - 管理员: 启用/禁用用户
# ============================================================
@auth_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@admin_required
def toggle_user_status(user_id):
    """管理员启用/禁用用户"""
    data = request.get_json()
    is_active = data.get("is_active", True)

    success = UserModel.set_active(user_id, is_active)
    if success:
        status_text = "启用" if is_active else "禁用"
        return jsonify({"success": True, "message": f"用户已{status_text}"}), 200
    else:
        return jsonify({"success": False, "message": "操作失败"}), 400


# ============================================================
# PUT /api/auth/users/<user_id>/role - 管理员: 设置用户角色
# ============================================================
@auth_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@admin_required
def set_user_role(user_id):
    """管理员设置用户角色"""
    data = request.get_json()
    role = data.get("role", "")

    if role not in ("admin", "user", "viewer"):
        return jsonify({"success": False, "message": "无效的角色，可选: admin, user, viewer"}), 400

    success = UserModel.set_role(user_id, role)
    if success:
        return jsonify({"success": True, "message": f"用户角色已设为 {role}"}), 200
    else:
        return jsonify({"success": False, "message": "操作失败"}), 400


# ============================================================
# GET /api/auth/quota - 获取当前用户额度信息 (PRD 8.1)
# 同时注册为 /api/v1/user/quota 以符合 PRD 规范
# ============================================================
@auth_bp.route("/quota", methods=["GET"])
@login_required
def get_user_quota(current_user):
    """
    获取当前用户的各类操作剩余额度

    响应体 (JSON):
    {
        "success": true,
        "user_id": 1,
        "plan": "pro",
        "scrape_remaining": 500,
        "analysis_remaining": 100,
        "3d_remaining": 20,
        "render_remaining": 10,
        "quotas": {
            "scrape": {"used": 50, "limit": 500, "remaining": 450},
            "analysis": {"used": 10, "limit": 100, "remaining": 90},
            "3d_generate": {"used": 5, "limit": 20, "remaining": 15},
            "render_video": {"used": 2, "limit": 10, "remaining": 8}
        }
    }
    """
    user_id = current_user.get("user_id") or current_user.get("id")

    try:
        from monetization.subscription import SubscriptionManager
        from auth.quota_middleware import check_quota_api

        # 获取用户订阅信息
        sub_info = SubscriptionManager.get_user_subscription(user_id)
        plan = sub_info.get("plan", "free") if sub_info else "free"

        # 获取各类额度
        quota_types = ["scrape", "analysis", "3d_generate", "render_video"]
        quotas = {}
        for qt in quota_types:
            quota_detail = check_quota_api(user_id, qt)
            quotas[qt] = {
                "used": quota_detail.get("used", 0),
                "limit": quota_detail.get("limit", 0),
                "remaining": quota_detail.get("remaining", 0),
            }

        return jsonify({
            "success": True,
            "user_id": user_id,
            "plan": plan,
            "scrape_remaining": quotas.get("scrape", {}).get("remaining", 0),
            "analysis_remaining": quotas.get("analysis", {}).get("remaining", 0),
            "3d_remaining": quotas.get("3d_generate", {}).get("remaining", 0),
            "render_remaining": quotas.get("render_video", {}).get("remaining", 0),
            "quotas": quotas,
        }), 200

    except Exception as e:
        logger.error(f"[Auth] 获取额度信息失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取额度信息失败: {str(e)}"
        }), 500
