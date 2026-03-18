"""
Coupang 选品系统 - APM 性能监控 API 路由
端点:
    GET /api/health              健康检查 (公开)
    GET /api/metrics             Prometheus 指标 (公开)
    GET /api/v1/admin/apm        APM 仪表盘数据 (管理员)
    GET /api/v1/admin/apm/slow   慢查询列表 (管理员)
"""

from flask import Blueprint, jsonify, Response
from auth.middleware import login_required
from utils.apm_monitor import metrics, get_health_status
from utils.logger import get_logger

logger = get_logger()

apm_bp = Blueprint("apm", __name__)


def _is_admin(current_user):
    return current_user.get("role") == "admin"


@apm_bp.route("/api/health", methods=["GET"])
def health_check():
    """
    健康检查端点 (公开)
    用于 K8s liveness/readiness probe 和负载均衡器
    """
    status = get_health_status()
    code = 200 if status["status"] == "healthy" else 503
    return jsonify(status), code


@apm_bp.route("/api/metrics", methods=["GET"])
def prometheus_metrics():
    """
    Prometheus 指标端点 (公开)
    返回 Prometheus 格式的文本指标
    """
    content = metrics.get_prometheus_metrics()
    return Response(content, mimetype="text/plain; charset=utf-8")


@apm_bp.route("/api/v1/admin/apm", methods=["GET"])
@login_required
def apm_dashboard(current_user):
    """APM 仪表盘数据 (管理员)"""
    if not _is_admin(current_user):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    data = metrics.get_metrics()
    health = get_health_status()

    return jsonify({
        "success": True,
        "health": health,
        "metrics": data,
    }), 200


@apm_bp.route("/api/v1/admin/apm/slow", methods=["GET"])
@login_required
def slow_queries(current_user):
    """慢查询列表 (管理员)"""
    if not _is_admin(current_user):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    data = metrics.get_metrics()
    return jsonify({
        "success": True,
        "slow_queries": data["database"]["slow_queries"],
        "total_queries": data["database"]["total_queries"],
        "avg_query_ms": data["database"]["avg_query_ms"],
    }), 200
