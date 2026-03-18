"""
Coupang 选品系统 - 数据清理管理 API 路由
端点:
    POST /api/v1/admin/cleanup/run         执行数据清理
    POST /api/v1/admin/cleanup/preview     预览清理结果
    GET  /api/v1/admin/cleanup/stats       获取存储统计
    POST /api/v1/projects/<id>/archive     归档项目
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required
from utils.data_cleaner import cleaner, CleanupPolicy
from utils.logger import get_logger

logger = get_logger()

cleanup_bp = Blueprint("cleanup", __name__, url_prefix="/api/v1")


def _uid(current_user):
    return current_user.get("user_id") or current_user.get("sub")


def _is_admin(current_user):
    return current_user.get("role") == "admin"


@cleanup_bp.route("/admin/cleanup/run", methods=["POST"])
@login_required
def run_cleanup(current_user):
    """执行数据清理（仅管理员）"""
    if not _is_admin(current_user):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    result = cleaner.run_all(dry_run=False)

    # 记录审计日志
    try:
        from utils.audit_logger import audit
        audit.log(
            action="data_cleanup",
            user_id=_uid(current_user),
            details={"total_cleaned": result.get("total_cleaned", 0)},
        )
    except Exception:
        pass

    return jsonify(result), 200


@cleanup_bp.route("/admin/cleanup/preview", methods=["POST"])
@login_required
def preview_cleanup(current_user):
    """预览清理结果（不实际删除）"""
    if not _is_admin(current_user):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    result = cleaner.run_all(dry_run=True)
    return jsonify(result), 200


@cleanup_bp.route("/admin/cleanup/stats", methods=["GET"])
@login_required
def storage_stats(current_user):
    """获取存储统计信息"""
    if not _is_admin(current_user):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    stats = cleaner.get_storage_stats()
    stats["policy"] = {
        "task_result_retention_days": CleanupPolicy.TASK_RESULT_RETENTION_DAYS,
        "audit_log_retention_days": CleanupPolicy.AUDIT_LOG_RETENTION_DAYS,
        "notification_retention_days": CleanupPolicy.NOTIFICATION_RETENTION_DAYS,
        "temp_file_retention_days": CleanupPolicy.TEMP_FILE_RETENTION_DAYS,
        "archive_enabled": CleanupPolicy.ARCHIVE_ENABLED,
    }
    return jsonify({"success": True, **stats}), 200


@cleanup_bp.route("/projects/<int:project_id>/archive", methods=["POST"])
@login_required
def archive_project(current_user, project_id):
    """归档项目"""
    result = cleaner.archive_project(project_id, _uid(current_user))
    status = 200 if result.get("success") else 400
    return jsonify(result), status
