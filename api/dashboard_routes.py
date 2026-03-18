"""
Dashboard API 路由
提供仪表盘所需的统计数据和活动图表数据

端点:
    GET /api/v1/dashboard/stats           获取仪表盘统计数据
    GET /api/v1/dashboard/activity-chart  获取最近 7 天活动图表数据
"""

import os
import sys
from datetime import datetime, timedelta

from flask import Blueprint, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.middleware import login_required
from utils.logger import get_logger

logger = get_logger()

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


def _get_db():
    """获取数据库连接（可降级）"""
    try:
        from database.connection import db
        db.fetch_one("SELECT 1")
        return db
    except Exception:
        return None


@dashboard_bp.route("/stats", methods=["GET"])
@login_required
def get_dashboard_stats(current_user):
    """
    获取仪表盘统计数据

    返回:
        active_projects: int - 活跃项目数
        products_analyzed: int - 已分析产品数
        models_3d: int - 3D 模型数
        recent_projects: list - 最近项目列表
    """
    user_id = current_user["user_id"]
    db = _get_db()

    stats = {
        "active_projects": 0,
        "products_analyzed": 0,
        "models_3d": 0,
    }

    if db:
        try:
            # 活跃项目数
            row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM sourcing_projects WHERE user_id = %s AND status != 'failed'",
                (user_id,),
            )
            stats["active_projects"] = row["cnt"] if row else 0
        except Exception:
            pass

        try:
            # 已分析产品数
            row = db.fetch_one(
                "SELECT COALESCE(SUM(product_count), 0) AS total FROM sourcing_projects WHERE user_id = %s",
                (user_id,),
            )
            stats["products_analyzed"] = int(row["total"]) if row else 0
        except Exception:
            pass

        try:
            # 3D 模型数
            row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM assets_3d WHERE user_id = %s AND status = 'completed'",
                (user_id,),
            )
            stats["models_3d"] = row["cnt"] if row else 0
        except Exception:
            pass
    else:
        # 降级到内存存储
        try:
            from api.project_routes import _projects
            user_projects = [p for p in _projects.values() if p.get("user_id") == user_id]
            stats["active_projects"] = len(user_projects)
            stats["products_analyzed"] = sum(p.get("product_count", 0) for p in user_projects)
        except Exception:
            pass

        try:
            from api.threed_routes import _mem_assets
            user_3d = [a for a in _mem_assets.values()
                       if a.get("user_id") == user_id and a.get("status") == "completed"]
            stats["models_3d"] = len(user_3d)
        except Exception:
            pass

    return jsonify({"success": True, "data": stats})


@dashboard_bp.route("/activity-chart", methods=["GET"])
@login_required
def get_activity_chart(current_user):
    """
    获取最近 7 天活动图表数据

    返回:
        labels: list[str] - 日期标签
        scrapes: list[int] - 每天抓取次数
        analyses: list[int] - 每天分析次数
    """
    user_id = current_user["user_id"]
    db = _get_db()

    now = datetime.now()
    labels = []
    scrape_data = [0] * 7
    analysis_data = [0] * 7

    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        labels.append(d.strftime("%a, %b %d"))

    if db:
        try:
            # 查询最近 7 天每天的项目创建数（作为抓取活动）
            rows = db.fetch_all("""
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                FROM sourcing_projects
                WHERE user_id = %s AND created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY day
            """, (user_id, (now - timedelta(days=6)).strftime("%Y-%m-%d")))

            day_map = {}
            for row in rows:
                day_str = str(row["day"])
                day_map[day_str] = row["cnt"]

            for idx, i in enumerate(range(6, -1, -1)):
                d = now - timedelta(days=i)
                day_key = d.strftime("%Y-%m-%d")
                scrape_data[idx] = day_map.get(day_key, 0)
        except Exception as e:
            logger.debug(f"查询抓取活动失败: {e}")

        try:
            # 查询最近 7 天每天的分析任务数
            rows = db.fetch_all("""
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                FROM analysis_tasks
                WHERE user_id = %s AND created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY day
            """, (user_id, (now - timedelta(days=6)).strftime("%Y-%m-%d")))

            day_map = {}
            for row in rows:
                day_str = str(row["day"])
                day_map[day_str] = row["cnt"]

            for idx, i in enumerate(range(6, -1, -1)):
                d = now - timedelta(days=i)
                day_key = d.strftime("%Y-%m-%d")
                analysis_data[idx] = day_map.get(day_key, 0)
        except Exception as e:
            logger.debug(f"查询分析活动失败: {e}")
    else:
        # 降级：从内存存储统计
        try:
            from api.project_routes import _projects
            for p in _projects.values():
                if p.get("user_id") != user_id:
                    continue
                created = p.get("created_at", "")
                if isinstance(created, str) and len(created) >= 10:
                    day_key = created[:10]
                    for idx, i in enumerate(range(6, -1, -1)):
                        d = now - timedelta(days=i)
                        if d.strftime("%Y-%m-%d") == day_key:
                            scrape_data[idx] += 1
                            break
        except Exception:
            pass

        try:
            from api.analysis_routes import _analysis_tasks
            for t in _analysis_tasks.values():
                if t.get("user_id") != user_id:
                    continue
                created = t.get("created_at", "")
                if isinstance(created, str) and len(created) >= 10:
                    day_key = created[:10]
                    for idx, i in enumerate(range(6, -1, -1)):
                        d = now - timedelta(days=i)
                        if d.strftime("%Y-%m-%d") == day_key:
                            analysis_data[idx] += 1
                            break
        except Exception:
            pass

    return jsonify({
        "success": True,
        "data": {
            "labels": labels,
            "scrapes": scrape_data,
            "analyses": analysis_data,
        },
    })
