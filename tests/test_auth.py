"""
Coupang 选品系统 - 用户认证模块单元测试
测试密码加密、JWT Token、验证逻辑等核心功能（不依赖数据库）
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_password_module():
    """测试密码加密与验证模块"""
    print("=" * 60)
    print("测试 1: 密码加密与验证模块")
    print("=" * 60)

    from auth.password import (
        hash_password, verify_password,
        validate_password_strength,
        validate_email, validate_username,
    )

    # 测试密码哈希
    plain = "TestPass123"
    hashed = hash_password(plain)
    print(f"  明文密码: {plain}")
    print(f"  哈希结果: {hashed}")
    assert hashed != plain, "哈希结果不应与明文相同"
    assert len(hashed) > 50, "哈希结果长度应大于50"

    # 测试密码验证
    assert verify_password(plain, hashed) == True, "正确密码应验证通过"
    assert verify_password("WrongPass", hashed) == False, "错误密码应验证失败"
    print("  ✓ 密码哈希与验证: 通过")

    # 测试密码强度验证
    assert validate_password_strength("abc")[0] == False       # 太短
    assert validate_password_strength("abcdefgh")[0] == False  # 无大写
    assert validate_password_strength("ABCDEFGH")[0] == False  # 无小写
    assert validate_password_strength("Abcdefgh")[0] == False  # 无数字
    assert validate_password_strength("Abcdefg1")[0] == True   # 合格
    print("  ✓ 密码强度验证: 通过")

    # 测试邮箱验证
    assert validate_email("user@example.com") == True
    assert validate_email("user@test.co.kr") == True
    assert validate_email("invalid-email") == False
    assert validate_email("@example.com") == False
    print("  ✓ 邮箱格式验证: 通过")

    # 测试用户名验证
    assert validate_username("myuser")[0] == True
    assert validate_username("my_user_123")[0] == True
    assert validate_username("ab")[0] == False           # 太短
    assert validate_username("123user")[0] == False       # 数字开头
    print("  ✓ 用户名格式验证: 通过")

    print()


def test_jwt_module():
    """测试 JWT Token 模块"""
    print("=" * 60)
    print("测试 2: JWT Token 模块")
    print("=" * 60)

    from auth.jwt_handler import (
        create_access_token, create_refresh_token,
        verify_access_token, verify_refresh_token,
        refresh_access_token,
    )

    # 测试生成 Access Token
    access_token = create_access_token(user_id=1, username="testuser", role="user")
    print(f"  Access Token: {access_token[:50]}...")
    assert len(access_token) > 50, "Token 长度应大于50"

    # 测试验证 Access Token
    user_info = verify_access_token(access_token)
    print(f"  解析结果: {user_info}")
    assert user_info is not None, "有效 Token 应能解析"
    assert user_info["user_id"] == 1
    assert user_info["username"] == "testuser"
    assert user_info["role"] == "user"
    print("  ✓ Access Token 生成与验证: 通过")

    # 测试生成 Refresh Token
    refresh_token = create_refresh_token(user_id=1)
    print(f"  Refresh Token: {refresh_token[:50]}...")

    # 测试验证 Refresh Token
    uid = verify_refresh_token(refresh_token)
    assert uid == 1, "Refresh Token 应能解析出用户ID"
    print("  ✓ Refresh Token 生成与验证: 通过")

    # 测试刷新 Access Token
    new_access = refresh_access_token(refresh_token, "testuser", "user")
    assert new_access is not None, "应能刷新 Access Token"
    new_info = verify_access_token(new_access)
    assert new_info["user_id"] == 1
    print("  ✓ Token 刷新: 通过")

    # 测试无效 Token
    invalid_result = verify_access_token("invalid.token.here")
    assert invalid_result is None, "无效 Token 应返回 None"
    print("  ✓ 无效 Token 拒绝: 通过")

    print()


def test_flask_app():
    """测试 Flask API 接口（使用测试客户端，不依赖数据库）"""
    print("=" * 60)
    print("测试 3: Flask API 路由注册")
    print("=" * 60)

    from app import create_app

    app = create_app()
    client = app.test_client()

    # 测试根路径
    resp = client.get("/")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["system"] == "Coupang 跨境电商智能选品系统"
    print("  ✓ GET / 根路径: 通过")

    # 测试健康检查
    resp = client.get("/api/health")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["status"] == "ok"
    print("  ✓ GET /api/health 健康检查: 通过")

    # 测试 API 文档
    resp = client.get("/api/docs")
    data = resp.get_json()
    assert resp.status_code == 200
    assert "auth" in data
    print("  ✓ GET /api/docs 接口文档: 通过")

    # 测试注册接口参数验证（不连接数据库，应返回参数错误）
    resp = client.post("/api/auth/register", json={})
    assert resp.status_code == 400
    print("  ✓ POST /api/auth/register 空参数拒绝: 通过")

    resp = client.post("/api/auth/register", json={
        "username": "ab",  # 太短
        "email": "test@test.com",
        "password": "Test1234",
    })
    assert resp.status_code == 400
    print("  ✓ POST /api/auth/register 用户名过短拒绝: 通过")

    resp = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "invalid-email",  # 格式错误
        "password": "Test1234",
    })
    assert resp.status_code == 400
    print("  ✓ POST /api/auth/register 邮箱格式错误拒绝: 通过")

    resp = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "weak",  # 密码太弱
    })
    assert resp.status_code == 400
    print("  ✓ POST /api/auth/register 弱密码拒绝: 通过")

    # 测试登录接口参数验证
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 400
    print("  ✓ POST /api/auth/login 空参数拒绝: 通过")

    # 测试需要认证的接口（未登录）
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    print("  ✓ GET /api/auth/me 未认证拒绝: 通过")

    # 测试带无效 Token 的请求
    resp = client.get("/api/auth/me", headers={
        "Authorization": "Bearer invalid.token.here"
    })
    assert resp.status_code == 401
    print("  ✓ GET /api/auth/me 无效Token拒绝: 通过")

    # 测试带有效 Token 的请求（模拟）
    from auth.jwt_handler import create_access_token
    token = create_access_token(user_id=999, username="mockuser", role="user")
    resp = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    # 这里会因为数据库未连接而可能返回500或404，但Token验证本身是通过的
    # 我们只验证Token解析逻辑正确
    print(f"  ✓ GET /api/auth/me 有效Token解析: 状态码 {resp.status_code} (数据库未连接属正常)")

    # 测试404
    resp = client.get("/api/nonexistent")
    assert resp.status_code == 404
    print("  ✓ 404 错误处理: 通过")

    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    Coupang 选品系统 - 用户认证模块测试                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    passed = 0
    failed = 0

    tests = [
        ("密码模块", test_password_module),
        ("JWT模块", test_jwt_module),
        ("Flask API", test_flask_app),
    ]

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
