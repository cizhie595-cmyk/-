"""
第三方 API 密钥配置 - REST API 路由

提供以下接口：
  GET  /api/keys/services         - 获取支持的服务列表
  GET  /api/keys/<service_id>     - 获取某服务的脱敏配置
  GET  /api/keys/all              - 获取所有服务的脱敏配置
  POST /api/keys/<service_id>     - 保存某服务的配置
  POST /api/keys/<service_id>/test - 测试某服务的连通性
  DELETE /api/keys/<service_id>   - 删除某服务的配置
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required
from auth.api_keys_config import APIKeysConfigManager

api_keys_bp = Blueprint("api_keys", __name__, url_prefix="/api/keys")


@api_keys_bp.route("/services", methods=["GET"])
@login_required
def get_services(current_user):
    """获取所有支持的第三方服务列表"""
    services = APIKeysConfigManager.get_services()
    return jsonify({"success": True, "services": services})


@api_keys_bp.route("/all", methods=["GET"])
@login_required
def get_all_configs(current_user):
    """获取所有服务的脱敏配置"""
    configs = APIKeysConfigManager.get_all_configs_safe(current_user["id"])
    return jsonify({"success": True, "configs": configs})


@api_keys_bp.route("/<service_id>", methods=["GET"])
@login_required
def get_service_config(current_user, service_id):
    """获取某服务的脱敏配置"""
    config = APIKeysConfigManager.get_safe_config(current_user["id"], service_id)
    return jsonify({"success": True, "config": config})


@api_keys_bp.route("/<service_id>", methods=["POST"])
@login_required
def save_service_config(current_user, service_id):
    """保存某服务的配置"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    success, message = APIKeysConfigManager.save_service_config(
        current_user["id"], service_id, data
    )

    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@api_keys_bp.route("/<service_id>/test", methods=["POST"])
@login_required
def test_service(current_user, service_id):
    """测试某服务的连通性"""
    success, message = APIKeysConfigManager.test_service(
        current_user["id"], service_id
    )

    return jsonify({"success": success, "message": message})


@api_keys_bp.route("/<service_id>", methods=["DELETE"])
@login_required
def delete_service_config(current_user, service_id):
    """删除某服务的配置"""
    success, message = APIKeysConfigManager.delete_service_config(
        current_user["id"], service_id
    )

    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code
