"""
Coupang 选品系统 - 数据导出 API 路由
支持: CSV / Excel (XLSX) / PDF 格式
端点:
    GET /api/v1/export/products/<project_id>   导出项目产品列表
    GET /api/v1/export/analysis/<task_id>      导出分析报告
    GET /api/v1/export/profit/<project_id>     导出利润计算结果
"""

from flask import Blueprint, request, send_file, jsonify
from auth.middleware import login_required
from utils.data_exporter import (
    DataExporter, PRODUCT_COLUMNS, ANALYSIS_COLUMNS, PROFIT_COLUMNS,
)
from utils.logger import get_logger

logger = get_logger()

export_bp = Blueprint("export", __name__, url_prefix="/api/v1/export")

ALLOWED_FORMATS = ("csv", "xlsx", "pdf")


def _get_db():
    """获取数据库连接"""
    try:
        from database.connection import db
        db.fetch_one("SELECT 1")
        return db
    except Exception:
        return None


# ============================================================
# GET /api/v1/export/products/<project_id>
# ============================================================
@export_bp.route("/products/<project_id>", methods=["GET"])
@login_required
def export_products(current_user, project_id):
    """
    导出项目产品列表

    Query params:
        format: csv / xlsx / pdf (默认 csv)
        columns: 逗号分隔的列名（可选，默认全部）
    """
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ALLOWED_FORMATS:
        return jsonify({"success": False, "message": f"不支持的格式: {fmt}，支持: csv/xlsx/pdf"}), 400

    user_id = current_user.get("user_id") or current_user.get("sub")
    db = _get_db()

    # 获取产品数据
    data = []
    if db:
        try:
            # 验证项目归属
            project = db.fetch_one(
                "SELECT id FROM sourcing_projects WHERE id = %s AND user_id = %s",
                (project_id, user_id),
            )
            if not project:
                return jsonify({"success": False, "message": "项目不存在或无权访问"}), 404

            rows = db.fetch_all(
                """SELECT asin, title, brand, price, rating, review_count,
                          bsr_rank, category, monthly_sales, revenue,
                          fba_fee, profit_margin, competition_level, opportunity_score
                   FROM project_products
                   WHERE project_id = %s
                   ORDER BY opportunity_score DESC""",
                (project_id,),
            )
            data = [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"[Export] 查询产品数据失败: {e}")
            # 使用示例数据
            data = _get_demo_products()
    else:
        data = _get_demo_products()

    # 处理列筛选
    columns = PRODUCT_COLUMNS
    col_filter = request.args.get("columns")
    if col_filter:
        keys = [k.strip() for k in col_filter.split(",")]
        columns = [c for c in PRODUCT_COLUMNS if c["key"] in keys]
        if not columns:
            columns = PRODUCT_COLUMNS

    # 导出
    filename = f"products_{project_id}"
    return _do_export(data, columns, fmt, filename, title=f"产品列表 - 项目 {project_id}")


# ============================================================
# GET /api/v1/export/analysis/<task_id>
# ============================================================
@export_bp.route("/analysis/<task_id>", methods=["GET"])
@login_required
def export_analysis(current_user, task_id):
    """导出分析报告"""
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ALLOWED_FORMATS:
        return jsonify({"success": False, "message": f"不支持的格式: {fmt}"}), 400

    user_id = current_user.get("user_id") or current_user.get("sub")
    db = _get_db()

    data = []
    if db:
        try:
            task = db.fetch_one(
                "SELECT id, result_json FROM analysis_tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            if not task:
                return jsonify({"success": False, "message": "分析任务不存在或无权访问"}), 404

            import json
            result = json.loads(task.get("result_json", "[]")) if task.get("result_json") else []
            if isinstance(result, list):
                data = result
            elif isinstance(result, dict):
                data = result.get("dimensions", [result])
        except Exception as e:
            logger.error(f"[Export] 查询分析数据失败: {e}")
            data = _get_demo_analysis()
    else:
        data = _get_demo_analysis()

    filename = f"analysis_{task_id}"
    return _do_export(data, ANALYSIS_COLUMNS, fmt, filename, title=f"分析报告 - 任务 {task_id}")


# ============================================================
# GET /api/v1/export/profit/<project_id>
# ============================================================
@export_bp.route("/profit/<project_id>", methods=["GET"])
@login_required
def export_profit(current_user, project_id):
    """导出利润计算结果"""
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ALLOWED_FORMATS:
        return jsonify({"success": False, "message": f"不支持的格式: {fmt}"}), 400

    user_id = current_user.get("user_id") or current_user.get("sub")
    db = _get_db()

    data = []
    if db:
        try:
            rows = db.fetch_all(
                """SELECT p.asin, p.title, p.price AS selling_price,
                          pc.cost_price, pc.fba_fee, pc.referral_fee,
                          pc.shipping_cost, pc.net_profit, pc.profit_margin, pc.roi
                   FROM project_products p
                   JOIN profit_calculations pc ON p.id = pc.product_id
                   WHERE p.project_id = %s
                   ORDER BY pc.profit_margin DESC""",
                (project_id,),
            )
            data = [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"[Export] 查询利润数据失败: {e}")
            data = _get_demo_profit()
    else:
        data = _get_demo_profit()

    filename = f"profit_{project_id}"
    return _do_export(data, PROFIT_COLUMNS, fmt, filename, title=f"利润计算 - 项目 {project_id}")


# ============================================================
# 通用导出函数
# ============================================================
def _do_export(data, columns, fmt, filename, title="数据导出"):
    """执行导出并返回文件响应"""
    exporter = DataExporter()

    try:
        if fmt == "csv":
            buf = exporter.export_csv(data, columns, filename)
            mimetype = "text/csv; charset=utf-8"
            ext = "csv"
        elif fmt == "xlsx":
            buf = exporter.export_excel(data, columns, filename=filename)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        elif fmt == "pdf":
            buf = exporter.export_pdf(data, columns, title=title, filename=filename)
            mimetype = "application/pdf"
            ext = "pdf"
        else:
            return jsonify({"success": False, "message": "不支持的格式"}), 400

        if buf is None:
            return jsonify({"success": False, "message": f"{fmt} 导出依赖未安装"}), 500

        # 记录审计日志
        try:
            from utils.audit_logger import audit, AuditLogger
            user_id = request.current_user.get("user_id") if hasattr(request, "current_user") else None
            audit.log(
                action=AuditLogger.ACTION_DATA_EXPORT,
                user_id=user_id,
                details={"format": fmt, "filename": filename, "rows": len(data)},
            )
        except Exception:
            pass

        return send_file(
            buf,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{filename}.{ext}",
        )

    except Exception as e:
        logger.error(f"[Export] 导出失败: {e}")
        return jsonify({"success": False, "message": f"导出失败: {str(e)}"}), 500


# ============================================================
# 演示数据（数据库不可用时的降级数据）
# ============================================================
def _get_demo_products():
    return [
        {"asin": "B09V3KXJPB", "title": "Wireless Earbuds", "brand": "SoundMax",
         "price": 29.99, "rating": 4.3, "review_count": 1250, "bsr_rank": 856,
         "category": "Electronics", "monthly_sales": 3200, "revenue": 95968.0,
         "fba_fee": 5.20, "profit_margin": 32.5, "competition_level": "Medium",
         "opportunity_score": 78},
        {"asin": "B0BN9KXJPB", "title": "Phone Case Ultra", "brand": "CasePro",
         "price": 12.99, "rating": 4.5, "review_count": 3400, "bsr_rank": 234,
         "category": "Cell Phone Accessories", "monthly_sales": 8500, "revenue": 110415.0,
         "fba_fee": 3.10, "profit_margin": 45.2, "competition_level": "High",
         "opportunity_score": 65},
    ]


def _get_demo_analysis():
    return [
        {"dimension": "市场容量", "score": 85, "summary": "月搜索量 50K+，需求稳定增长",
         "recommendation": "建议进入"},
        {"dimension": "竞争强度", "score": 62, "summary": "Top10 卖家评论均值 2000+",
         "recommendation": "需差异化策略"},
        {"dimension": "利润空间", "score": 78, "summary": "平均利润率 30%+",
         "recommendation": "利润可观"},
    ]


def _get_demo_profit():
    return [
        {"asin": "B09V3KXJPB", "title": "Wireless Earbuds", "selling_price": 29.99,
         "cost_price": 8.50, "fba_fee": 5.20, "referral_fee": 4.50,
         "shipping_cost": 2.30, "net_profit": 9.49, "profit_margin": 31.6, "roi": 87.5},
    ]
