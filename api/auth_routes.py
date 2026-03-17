"""
Coupang 选品系统 - 用户认证 API 路由
提供: 注册、登录、Token刷新、登出 等接口
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
)
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

    return jsonify({
        "success": True,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "username": username,
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
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
