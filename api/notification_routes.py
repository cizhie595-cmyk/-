"""
Coupang 选品系统 - 通知 API 路由
端点:
    GET    /api/v1/notifications              获取通知列表
    GET    /api/v1/notifications/unread-count  获取未读数
    POST   /api/v1/notifications/mark-read    标记已读
    DELETE /api/v1/notifications               删除通知
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required
from utils.notification_manager import notifier
from utils.logger import get_logger

logger = get_logger()

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


def _uid(current_user):
    return current_user.get("user_id") or current_user.get("sub")


@notification_bp.route("", methods=["GET"])
@login_required
def get_notifications(current_user):
    """获取通知列表"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"

    result = notifier.get_notifications(
        user_id=_uid(current_user),
        page=page,
        per_page=min(per_page, 100),
        unread_only=unread_only,
    )
    return jsonify(result), 200


@notification_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count(current_user):
    """获取未读通知数量"""
    result = notifier.get_notifications(
        user_id=_uid(current_user), page=1, per_page=1, unread_only=True,
    )
    return jsonify({
        "success": True,
        "unread_count": result.get("unread_count", 0),
    }), 200


@notification_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_read(current_user):
    """
    标记通知为已读

    Body: {"ids": [1,2,3]}  或 {"all": true}
    """
    data = request.get_json(silent=True) or {}
    ids = data.get("ids")
    mark_all = data.get("all", False)

    if mark_all:
        result = notifier.mark_read(_uid(current_user))
    elif ids:
        result = notifier.mark_read(_uid(current_user), ids)
    else:
        return jsonify({"success": False, "message": "请提供 ids 或 all 参数"}), 400

    return jsonify(result), 200


@notification_bp.route("", methods=["DELETE"])
@login_required
def delete_notifications(current_user):
    """
    删除通知

    Body: {"ids": [1,2,3]}
    """
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"success": False, "message": "请提供要删除的通知 ID"}), 400

    result = notifier.delete_notifications(_uid(current_user), ids)
    return jsonify(result), 200
