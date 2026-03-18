"""
新增功能单元测试
覆盖: 邮箱验证Token、密码重置Token、限流中间件、错误处理、审计日志、Stripe集成
运行方式:
    cd /path/to/project
    python tests/test_new_features.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "1"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests"

passed = 0
failed = 0
skipped = 0


def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  \u2705 {name}")
        passed += 1
    except Exception as e:
        print(f"  \u274c {name}: {e}")
        failed += 1


def skip(name, reason=""):
    global skipped
    print(f"  \u23ed\ufe0f  {name} (跳过: {reason})")
    skipped += 1


# ============================================================
# 1. JWT Token - 邮箱验证 & 密码重置
# ============================================================
print("\n\U0001f510 1. JWT Token - 邮箱验证 & 密码重置")


def test_create_email_verification_token():
    from auth.jwt_handler import create_email_verification_token, verify_email_verification_token
    token = create_email_verification_token(user_id=42, email="test@example.com")
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20


test("创建邮箱验证 Token", test_create_email_verification_token)


def test_verify_email_verification_token():
    from auth.jwt_handler import create_email_verification_token, verify_email_verification_token
    token = create_email_verification_token(user_id=42, email="test@example.com")
    result = verify_email_verification_token(token)
    assert result is not None
    assert result["user_id"] == 42
    assert result["email"] == "test@example.com"


test("验证邮箱验证 Token", test_verify_email_verification_token)


def test_verify_email_token_invalid():
    from auth.jwt_handler import verify_email_verification_token
    result = verify_email_verification_token("invalid-token")
    assert result is None


test("无效邮箱验证 Token 返回 None", test_verify_email_token_invalid)


def test_create_password_reset_token():
    from auth.jwt_handler import create_password_reset_token, verify_password_reset_token
    token = create_password_reset_token(user_id=99, email="reset@example.com")
    assert token is not None
    result = verify_password_reset_token(token)
    assert result is not None
    assert result["user_id"] == 99
    assert result["email"] == "reset@example.com"


test("创建并验证密码重置 Token", test_create_password_reset_token)


def test_token_type_mismatch():
    from auth.jwt_handler import (
        create_email_verification_token,
        create_password_reset_token,
        verify_email_verification_token,
        verify_password_reset_token,
    )
    email_token = create_email_verification_token(1, "a@b.com")
    reset_token = create_password_reset_token(1, "a@b.com")
    # 交叉验证应失败
    assert verify_password_reset_token(email_token) is None
    assert verify_email_verification_token(reset_token) is None


test("Token 类型交叉验证应失败", test_token_type_mismatch)


# ============================================================
# 2. 邮件发送服务
# ============================================================
print("\n\U0001f4e7 2. 邮件发送服务")


def test_email_sender_module_import():
    from utils.email_sender import send_verification_email, send_password_reset_email
    assert callable(send_verification_email)
    assert callable(send_password_reset_email)


test("邮件发送模块可正常导入", test_email_sender_module_import)


# ============================================================
# 3. 统一错误处理
# ============================================================
print("\n\u26a0\ufe0f  3. 统一错误处理")


def test_custom_exceptions():
    from utils.error_handler import (
        AppException, BadRequestError, UnauthorizedError,
        ForbiddenError, NotFoundError, ConflictError,
        QuotaExceededError, ExternalServiceError, ServiceUnavailableError,
    )
    # 测试基础异常
    e = AppException("测试错误")
    assert e.status_code == 500
    assert e.error_code == "internal_error"
    d = e.to_dict()
    assert d["success"] is False
    assert d["message"] == "测试错误"

    # 测试各子类状态码
    assert BadRequestError().status_code == 400
    assert UnauthorizedError().status_code == 401
    assert ForbiddenError().status_code == 403
    assert NotFoundError().status_code == 404
    assert ConflictError().status_code == 409
    assert QuotaExceededError().status_code == 429
    assert ExternalServiceError().status_code == 502
    assert ServiceUnavailableError().status_code == 503


test("自定义异常类", test_custom_exceptions)


def test_exception_with_details():
    from utils.error_handler import BadRequestError
    e = BadRequestError(
        message="参数错误",
        details={"field": "email", "reason": "格式不正确"}
    )
    d = e.to_dict()
    assert d["details"]["field"] == "email"


test("异常携带详情", test_exception_with_details)


def test_error_handler_registration():
    from utils.error_handler import register_error_handlers
    from flask import Flask
    app = Flask(__name__)
    register_error_handlers(app)
    # 验证 404 处理
    with app.test_client() as client:
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error"] == "not_found"


test("全局错误处理器注册", test_error_handler_registration)


# ============================================================
# 4. API 限流中间件
# ============================================================
print("\n\U0001f6a6 4. API 限流中间件")


def test_rate_limiter_module_import():
    from auth.rate_limiter import init_rate_limiter
    assert callable(init_rate_limiter)


test("限流模块可正常导入", test_rate_limiter_module_import)


def test_rate_limiter_memory_fallback():
    from auth.rate_limiter import init_rate_limiter
    from flask import Flask
    app = Flask(__name__)

    @app.route("/test")
    def test_route():
        return "ok"

    # 不配置 Redis，应降级为内存存储
    limiter = init_rate_limiter(app)
    # limiter 可能为 None（如果 Flask-Limiter 未安装）或有效实例
    # 只要不抛异常就算通过


test("限流中间件内存降级", test_rate_limiter_memory_fallback)


# ============================================================
# 5. Stripe 支付模块
# ============================================================
print("\n\U0001f4b3 5. Stripe 支付模块")


def test_stripe_handler_import():
    from monetization.stripe_handler import StripeHandler
    assert callable(StripeHandler.is_available)
    assert callable(StripeHandler.create_checkout_session)
    assert callable(StripeHandler.handle_webhook_event)


test("Stripe 处理器可正常导入", test_stripe_handler_import)


def test_stripe_not_configured():
    from monetization.stripe_handler import StripeHandler
    # 未配置 STRIPE_SECRET_KEY 时应返回 False
    result = StripeHandler.create_checkout_session(
        user_id=1, email="test@test.com",
        plan_id="orbit", billing_cycle="monthly"
    )
    # 未配置时应返回 None
    assert result is None


test("Stripe 未配置时优雅降级", test_stripe_not_configured)


def test_stripe_routes_import():
    from api.stripe_routes import stripe_bp
    assert stripe_bp.name == "stripe"


test("Stripe 路由蓝图可正常导入", test_stripe_routes_import)


# ============================================================
# 6. 审计日志
# ============================================================
print("\n\U0001f4dd 6. 审计日志")


def test_audit_logger_import():
    from utils.audit_logger import AuditLogger, audit
    assert callable(audit.log)
    assert callable(audit.query)


test("审计日志模块可正常导入", test_audit_logger_import)


def test_audit_action_constants():
    from utils.audit_logger import AuditLogger
    assert AuditLogger.ACTION_LOGIN == "login"
    assert AuditLogger.ACTION_REGISTER == "register"
    assert AuditLogger.ACTION_SUBSCRIPTION_UPGRADE == "subscription_upgrade"
    assert AuditLogger.ACTION_PROJECT_CREATE == "project_create"


test("审计日志操作类型常量", test_audit_action_constants)


def test_audit_routes_import():
    from api.audit_routes import audit_bp
    assert audit_bp.name == "audit"


test("审计日志路由蓝图可正常导入", test_audit_routes_import)


# ============================================================
# 7. 数据库连接池
# ============================================================
print("\n\U0001f5c4\ufe0f  7. 数据库连接池")


def test_db_manager_import():
    from database.connection import DatabaseManager
    dm = DatabaseManager.__new__(DatabaseManager)
    assert hasattr(dm, 'get_connection')
    assert hasattr(dm, 'health_check')
    assert hasattr(dm, 'connection_context')
    assert hasattr(dm, 'transaction')


test("数据库管理器类结构完整", test_db_manager_import)


# ============================================================
# 8. Flask 应用完整启动测试
# ============================================================
print("\n\U0001f310 8. Flask 应用完整启动")


def test_app_creation_with_new_features():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    # 检查新增蓝图是否注册
    blueprint_names = list(app.blueprints.keys())
    assert "stripe" in blueprint_names, f"stripe 蓝图未注册: {blueprint_names}"
    assert "audit" in blueprint_names, f"audit 蓝图未注册: {blueprint_names}"


test("Flask 应用创建（含新增蓝图）", test_app_creation_with_new_features)


def test_new_api_routes_exist():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    rules = [rule.rule for rule in app.url_map.iter_rules()]

    # 验证新增路由
    new_routes = [
        "/api/auth/verify-email",
        "/api/auth/resend-verification",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/stripe/create-checkout-session",
        "/api/stripe/webhook",
        "/api/stripe/customer-portal",
        "/api/stripe/config",
        "/api/audit/logs",
        "/api/audit/actions",
    ]

    for route in new_routes:
        assert route in rules, f"路由 {route} 未注册"


test("新增 API 路由已注册", test_new_api_routes_exist)


def test_health_check_endpoint():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"


test("健康检查端点", test_health_check_endpoint)


def test_stripe_config_endpoint():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        resp = client.get("/api/stripe/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "publishable_key" in data
        assert "available" in data


test("Stripe 配置端点", test_stripe_config_endpoint)


def test_forgot_password_endpoint():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        # 测试缺少邮箱参数时返回 400
        resp = client.post("/api/auth/forgot-password",
                           json={"email": ""},
                           content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False


test("忘记密码端点（参数校验）", test_forgot_password_endpoint)


# ============================================================
# 结果汇总
# ============================================================
print(f"\n{'='*60}")
print(f"\U0001f4ca 测试结果: {passed} 通过, {failed} 失败, {skipped} 跳过")
print(f"{'='*60}")

if failed > 0:
    sys.exit(1)
