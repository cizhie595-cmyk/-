"""
竞品监控 API 路由

提供竞品添加/删除/列表、快照抓取、变化检测、趋势数据、对比矩阵等端点。
"""

from flask import Blueprint, request, jsonify
from utils.logger import get_logger

logger = get_logger()

competitor_bp = Blueprint("competitor", __name__, url_prefix="/api/v1/competitor")


def _get_db():
    """获取数据库连接"""
    try:
        from database.connection import get_db
        return get_db()
    except Exception:
        return None


def _get_tracker(db=None):
    """创建 CompetitorTracker 实例"""
    from analysis.competitor_tracker import CompetitorTracker
    from utils.http_client import HttpClient
    return CompetitorTracker(db=db, http_client=HttpClient())


# ================================================================
# 监控列表管理
# ================================================================

@competitor_bp.route("/monitors", methods=["GET"])
def list_monitors():
    """获取竞品监控列表"""
    user_id = request.args.get("user_id", 1, type=int)
    project_id = request.args.get("project_id", type=int)

    db = _get_db()
    tracker = _get_tracker(db)
    monitors = tracker.list_competitors(user_id, project_id)

    return jsonify({"success": True, "data": monitors, "count": len(monitors)})


@competitor_bp.route("/monitors", methods=["POST"])
def add_monitor():
    """添加竞品监控"""
    data = request.get_json() or {}
    user_id = data.get("user_id", 1)
    project_id = data.get("project_id", 0)
    asin = data.get("asin", "")
    label = data.get("label", "")
    notes = data.get("notes", "")

    if not asin:
        return jsonify({"success": False, "error": "ASIN is required"}), 400

    db = _get_db()
    tracker = _get_tracker(db)
    record = tracker.add_competitor(user_id, project_id, asin, label, notes)

    return jsonify({"success": True, "data": record})


@competitor_bp.route("/monitors/<int:monitor_id>", methods=["DELETE"])
def remove_monitor(monitor_id):
    """移除竞品监控"""
    user_id = request.args.get("user_id", 1, type=int)

    db = _get_db()
    tracker = _get_tracker(db)
    success = tracker.remove_competitor(user_id, monitor_id)

    return jsonify({"success": success})


# ================================================================
# 数据快照
# ================================================================

@competitor_bp.route("/snapshot/<asin>", methods=["POST"])
def take_snapshot(asin):
    """抓取单个竞品快照"""
    data = request.get_json() or {}
    user_id = data.get("user_id", 1)
    monitor_id = data.get("monitor_id", 0)

    db = _get_db()
    tracker = _get_tracker(db)
    snapshot = tracker.take_snapshot(asin)

    if monitor_id:
        tracker.save_snapshot(user_id, monitor_id, snapshot)

    return jsonify({"success": True, "data": snapshot})


@competitor_bp.route("/snapshot/batch", methods=["POST"])
def batch_snapshot():
    """批量抓取所有监控竞品快照"""
    data = request.get_json() or {}
    user_id = data.get("user_id", 1)
    project_id = data.get("project_id")

    db = _get_db()
    tracker = _get_tracker(db)
    results = tracker.batch_snapshot(user_id, project_id)

    return jsonify({"success": True, "data": results, "count": len(results)})


# ================================================================
# 变化检测
# ================================================================

@competitor_bp.route("/alerts/<int:monitor_id>", methods=["GET"])
def get_alerts(monitor_id):
    """获取竞品变化告警"""
    db = _get_db()
    tracker = _get_tracker(db)
    alerts = tracker.detect_changes(monitor_id)

    return jsonify({"success": True, "data": alerts, "count": len(alerts)})


# ================================================================
# 趋势数据
# ================================================================

@competitor_bp.route("/trend/<int:monitor_id>", methods=["GET"])
def get_trend(monitor_id):
    """获取竞品指标趋势数据"""
    days = request.args.get("days", 30, type=int)
    metric = request.args.get("metric", "price")

    db = _get_db()
    tracker = _get_tracker(db)
    trend = tracker.get_trend_data(monitor_id, days, metric)

    return jsonify({"success": True, "data": trend})


# ================================================================
# 对比矩阵
# ================================================================

@competitor_bp.route("/matrix", methods=["GET"])
def get_comparison_matrix():
    """获取竞品对比矩阵"""
    user_id = request.args.get("user_id", 1, type=int)
    project_id = request.args.get("project_id", 0, type=int)

    db = _get_db()
    tracker = _get_tracker(db)
    matrix = tracker.generate_comparison_matrix(user_id, project_id)

    return jsonify({"success": True, "data": matrix})
