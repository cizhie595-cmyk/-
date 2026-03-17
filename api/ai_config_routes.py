"""
Coupang 选品系统 - AI 模型配置 API 路由

提供:
  GET  /api/ai/providers       - 获取支持的 AI 服务商列表
  GET  /api/ai/settings        - 获取当前用户的 AI 配置（脱敏）
  POST /api/ai/settings        - 保存/更新 AI 配置
  POST /api/ai/test            - 测试 API Key 连通性
  POST /api/ai/test-direct     - 直接测试（不保存，用于填写时即时验证）
"""

from flask import Blueprint, request, jsonify, g

from auth.ai_config import AIConfigManager
from auth.middleware import login_required
from utils.logger import get_logger

logger = get_logger()

# 创建 Blueprint
ai_config_bp = Blueprint("ai_config", __name__, url_prefix="/api/ai")


# ============================================================
# GET /api/ai/providers - 获取支持的 AI 服务商列表
# ============================================================
@ai_config_bp.route("/providers", methods=["GET"])
def get_providers():
    """
    获取所有支持的 AI 服务商信息（无需登录）

    返回每个服务商的名称、默认 Base URL 和可选模型列表，
    供前端下拉菜单使用。
    """
    providers = AIConfigManager.get_providers()

    return jsonify({
        "success": True,
        "data": providers,
    }), 200


# ============================================================
# GET /api/ai/settings - 获取当前用户的 AI 配置
# ============================================================
@ai_config_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    """
    获取当前登录用户的 AI 模型配置（API Key 已脱敏）

    返回:
    {
        "provider": "openai",
        "api_key_masked": "sk-pro...wxyz",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4000,
        "configured": true,
        "last_tested_at": "2026-03-18T12:00:00",
        "test_status": "success"
    }
    """
    user_id = g.current_user["user_id"]
    settings = AIConfigManager.get_safe_settings(user_id)

    return jsonify({
        "success": True,
        "data": settings,
    }), 200


# ============================================================
# POST /api/ai/settings - 保存/更新 AI 配置
# ============================================================
@ai_config_bp.route("/settings", methods=["POST"])
@login_required
def save_settings():
    """
    保存或更新当前用户的 AI 模型配置

    请求体 (JSON):
    {
        "provider": "openai",          // 必填: openai, deepseek, siliconflow, zhipu, custom
        "api_key": "sk-...",           // 必填: API Key
        "base_url": "",                // 可选: 自定义 Base URL（留空则使用服务商默认值）
        "model": "gpt-4o",            // 可选: 模型名称（留空则使用服务商默认模型）
        "temperature": 0.3,            // 可选: 温度参数 (0-2)
        "max_tokens": 4000             // 可选: 最大输出 Token 数
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    user_id = g.current_user["user_id"]
    success, message = AIConfigManager.save_settings(user_id, data)

    if success:
        # 返回保存后的脱敏配置
        safe_settings = AIConfigManager.get_safe_settings(user_id)
        return jsonify({
            "success": True,
            "message": message,
            "data": safe_settings,
        }), 200
    else:
        return jsonify({"success": False, "message": message}), 400


# ============================================================
# POST /api/ai/test - 测试已保存的 API Key 连通性
# ============================================================
@ai_config_bp.route("/test", methods=["POST"])
@login_required
def test_connection():
    """
    测试当前用户已保存的 AI 配置是否可用

    无需请求体，直接从数据库读取该用户的配置进行测试。
    会向 AI 服务商发送一个简单的 Hello 请求验证连通性。
    """
    user_id = g.current_user["user_id"]
    success, message = AIConfigManager.test_connection(user_id=user_id)

    return jsonify({
        "success": success,
        "message": message,
    }), 200 if success else 400


# ============================================================
# POST /api/ai/test-direct - 直接测试（不保存）
# ============================================================
@ai_config_bp.route("/test-direct", methods=["POST"])
@login_required
def test_direct():
    """
    直接测试传入的 AI 配置（不保存到数据库）

    适用于用户在填写表单时，点击"测试连接"按钮即时验证。

    请求体 (JSON):
    {
        "provider": "openai",
        "api_key": "sk-...",
        "base_url": "",
        "model": "gpt-4o"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    api_key = data.get("api_key", "").strip()
    if not api_key:
        return jsonify({"success": False, "message": "API Key 不能为空"}), 400

    # 构建临时配置
    from auth.ai_config import AI_PROVIDERS
    provider = data.get("provider", "openai")
    base_url = data.get("base_url", "").strip()
    if not base_url:
        base_url = AI_PROVIDERS.get(provider, {}).get(
            "default_base_url", "https://api.openai.com/v1"
        )

    test_settings = {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "model": data.get("model", "gpt-4o"),
    }

    success, message = AIConfigManager.test_connection(settings=test_settings)

    return jsonify({
        "success": success,
        "message": message,
    }), 200 if success else 400
