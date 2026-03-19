"""
深度分析 API 路由
对应 PRD 8.4 - Analysis

端点:
    POST /api/v1/analysis/visual              发起视觉语义分析
    POST /api/v1/analysis/reviews             发起评论深度挖掘
    GET  /api/v1/analysis/{task_id}/result    获取分析结果
    POST /api/v1/analysis/report/generate     生成综合决策报告
    GET  /api/v1/analysis/market              获取市场分析数据
    GET  /api/v1/analysis/report/{project_id} 获取报告数据
"""

import json
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/v1/analysis")


# ============================================================
# 数据库辅助函数
# ============================================================

def _get_db():
    """获取数据库连接（优雅降级到内存模式）"""
    try:
        from database.connection import db
        db.fetch_one("SELECT 1")
        return db
    except Exception:
        return None


# 内存降级存储
_mem_tasks = {}


def _db_create_task(db, task_data: dict) -> int:
    """在数据库中创建分析任务，返回任务ID"""
    return db.insert_and_get_id("""
        INSERT INTO analysis_tasks
        (task_type, user_id, project_id, asin, status, dimensions, review_count)
        VALUES (%s, %s, %s, %s, 'pending', %s, %s)
    """, (
        task_data["task_type"],
        task_data["user_id"],
        task_data.get("project_id"),
        task_data.get("asin"),
        json.dumps(task_data.get("dimensions")) if task_data.get("dimensions") else None,
        task_data.get("review_count", 500),
    ))


def _db_get_task(db, task_id, user_id: int) -> dict | None:
    """从数据库获取任务"""
    row = db.fetch_one("""
        SELECT id AS task_id, task_type, user_id, project_id, asin, status,
               dimensions, review_count, visual_usps, trust_signals,
               pain_points, buyer_persona, risk_score, report_url,
               result_data, error_message, started_at, completed_at,
               created_at, updated_at
        FROM analysis_tasks
        WHERE id = %s AND user_id = %s
    """, (task_id, user_id))
    if row:
        row["task_id"] = str(row["task_id"])
        for field in ("dimensions", "visual_usps", "trust_signals", "pain_points", "result_data"):
            if row.get(field) and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        for field in ("started_at", "completed_at", "created_at", "updated_at"):
            if row.get(field) and hasattr(row[field], "isoformat"):
                row[field] = row[field].isoformat()
    return row


def _db_update_task(db, task_id, **kwargs):
    """更新任务字段"""
    sets = []
    params = []
    for key, val in kwargs.items():
        sets.append(f"{key} = %s")
        if isinstance(val, (dict, list)):
            params.append(json.dumps(val, ensure_ascii=False, default=str))
        else:
            params.append(val)
    params.append(task_id)
    db.execute(
        f"UPDATE analysis_tasks SET {', '.join(sets)} WHERE id = %s",
        tuple(params)
    )


# ============================================================
# 视觉语义分析
# ============================================================

@analysis_bp.route("/visual", methods=["POST"])
@login_required
@quota_required("analysis")
def visual_analysis(current_user):
    """发起视觉语义分析"""
    data = request.get_json() or {}

    asin = data.get("asin", "").strip()
    if not asin:
        return jsonify({"success": False, "error": "请提供 ASIN"}), 400

    dimensions = data.get("dimensions", [
        "listing_quality", "review_health", "fulfillment", "variants", "opportunities"
    ])

    user_id = current_user["user_id"]
    task_data = {
        "task_type": "visual",
        "user_id": user_id,
        "asin": asin,
        "dimensions": dimensions,
    }

    db = _get_db()
    if db:
        task_id = _db_create_task(db, task_data)
        task_id_str = str(task_id)
    else:
        import uuid
        task_id_str = str(uuid.uuid4())[:12]
        _mem_tasks[task_id_str] = {
            **task_data,
            "task_id": task_id_str,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

    # 尝试 Celery 异步
    celery_dispatched = False
    try:
        from tasks.analysis_tasks import run_visual_analysis
        run_visual_analysis.delay(
            task_id=task_id_str if not db else task_id,
            asin=asin,
            user_id=user_id,
            dimensions=dimensions,
        )
        celery_dispatched = True
        logger.info(f"视觉分析任务已推入 Celery: task_id={task_id_str}")
    except Exception as e:
        logger.warning(f"Celery 不可用，降级到同步: {e}")

    if not celery_dispatched:
        _execute_visual_sync(task_id_str if not db else task_id, asin, user_id, db)

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id_str,
            "status": "pending",
        },
    })


def _execute_visual_sync(task_id, asin: str, user_id: int, db):
    """同步执行视觉分析"""
    try:
        if db:
            _db_update_task(db, task_id, status="processing", started_at=datetime.now())

        from scrapers.amazon.deep_crawler import AmazonDeepCrawler
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        crawler = AmazonDeepCrawler(ai_client=ai_client)

        try:
            result = crawler.deep_analyze(asin)
        finally:
            crawler.close()

        if result:
            update_fields = {
                "status": "completed",
                "result_data": result,
                "visual_usps": result.get("opportunities", []),
                "trust_signals": result.get("assessment", {}).get("listing_quality", {}),
                "risk_score": result.get("assessment", {}).get("overall_score"),
                "completed_at": datetime.now(),
            }
        else:
            update_fields = {"status": "failed", "error_message": "分析未返回结果"}

        if db:
            _db_update_task(db, task_id, **update_fields)
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)].update(update_fields)

    except Exception as e:
        if db:
            _db_update_task(db, task_id, status="failed", error_message=str(e))
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)]["status"] = "failed"
            _mem_tasks[str(task_id)]["error_message"] = str(e)
        logger.error(f"视觉分析任务失败: {e}")


# ============================================================
# 评论深度挖掘
# ============================================================

@analysis_bp.route("/reviews", methods=["POST"])
@login_required
@quota_required("analysis")
def review_analysis(current_user):
    """发起评论深度挖掘"""
    data = request.get_json() or {}

    asin = data.get("asin", "").strip()
    if not asin:
        return jsonify({"success": False, "error": "请提供 ASIN"}), 400

    review_count = data.get("review_count", 500)
    user_id = current_user["user_id"]

    task_data = {
        "task_type": "reviews",
        "user_id": user_id,
        "asin": asin,
        "review_count": review_count,
    }

    db = _get_db()
    if db:
        task_id = _db_create_task(db, task_data)
        task_id_str = str(task_id)
    else:
        import uuid
        task_id_str = str(uuid.uuid4())[:12]
        _mem_tasks[task_id_str] = {
            **task_data,
            "task_id": task_id_str,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

    # 尝试 Celery 异步
    celery_dispatched = False
    try:
        from tasks.analysis_tasks import run_review_analysis
        run_review_analysis.delay(
            task_id=task_id_str if not db else task_id,
            asin=asin,
            user_id=user_id,
            max_reviews=review_count,
        )
        celery_dispatched = True
        logger.info(f"评论分析任务已推入 Celery: task_id={task_id_str}")
    except Exception as e:
        logger.warning(f"Celery 不可用，降级到同步: {e}")

    if not celery_dispatched:
        _execute_review_sync(task_id_str if not db else task_id, asin, user_id, review_count, db)

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id_str,
            "status": "pending",
        },
    })


def _execute_review_sync(task_id, asin: str, user_id: int, max_reviews: int, db):
    """同步执行评论分析"""
    try:
        if db:
            _db_update_task(db, task_id, status="processing", started_at=datetime.now())

        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)

        review_crawler = AmazonReviewCrawler()
        try:
            reviews = review_crawler.crawl_reviews(asin, max_reviews=max_reviews)
        finally:
            review_crawler.close()

        if not reviews:
            update_fields = {
                "status": "completed",
                "result_data": {"message": "未找到评论数据"},
                "completed_at": datetime.now(),
            }
        else:
            analyzer = ReviewAnalyzer(ai_client=ai_client)
            analysis = analyzer.analyze(reviews, asin)
            update_fields = {
                "status": "completed",
                "result_data": analysis,
                "pain_points": analysis.get("pain_points", []),
                "buyer_persona": analysis.get("buyer_persona", ""),
                "completed_at": datetime.now(),
            }

        if db:
            _db_update_task(db, task_id, **update_fields)
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)].update(update_fields)

    except Exception as e:
        if db:
            _db_update_task(db, task_id, status="failed", error_message=str(e))
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)]["status"] = "failed"
            _mem_tasks[str(task_id)]["error_message"] = str(e)
        logger.error(f"评论分析任务失败: {e}")


# ============================================================
# 获取分析结果
# ============================================================

@analysis_bp.route("/<task_id>/result", methods=["GET"])
@login_required
def get_analysis_result(current_user, task_id):
    """获取分析结果"""
    user_id = current_user["user_id"]

    db = _get_db()
    if db:
        task = _db_get_task(db, task_id, user_id)
    else:
        task = _mem_tasks.get(task_id)
        if task and task["user_id"] != user_id:
            task = None

    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404

    response = {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "status": task["status"],
        "asin": task.get("asin"),
        "created_at": task.get("created_at"),
    }

    if task["status"] == "completed":
        response["result"] = task.get("result_data")
        response["visual_usps"] = task.get("visual_usps")
        response["trust_signals"] = task.get("trust_signals")
        response["pain_points"] = task.get("pain_points")
        response["buyer_persona"] = task.get("buyer_persona")
        response["risk_score"] = task.get("risk_score")
        response["report_url"] = task.get("report_url")
        response["completed_at"] = task.get("completed_at")
    elif task["status"] == "failed":
        response["error"] = task.get("error_message")

    return jsonify({"success": True, "data": response})


# ============================================================
# 综合决策报告
# ============================================================

@analysis_bp.route("/report/generate", methods=["POST"])
@login_required
@quota_required("analysis")
def generate_report(current_user):
    """生成综合决策报告"""
    data = request.get_json() or {}

    project_id = data.get("project_id")
    asin_list = data.get("asin_list", [])
    include_sections = data.get("include_sections", [
        "market_overview", "competitor_analysis", "profit_analysis",
        "risk_assessment", "recommendation"
    ])

    if not project_id and not asin_list:
        return jsonify({"success": False, "error": "请提供项目ID或ASIN列表"}), 400

    user_id = current_user["user_id"]
    task_data = {
        "task_type": "report",
        "user_id": user_id,
        "project_id": project_id,
        "asin": ",".join(asin_list) if asin_list else None,
    }

    db = _get_db()
    if db:
        task_id = _db_create_task(db, task_data)
        task_id_str = str(task_id)
    else:
        import uuid
        task_id_str = str(uuid.uuid4())[:12]
        _mem_tasks[task_id_str] = {
            **task_data,
            "task_id": task_id_str,
            "status": "pending",
            "include_sections": include_sections,
            "asin_list": asin_list,
            "created_at": datetime.now().isoformat(),
        }

    # 尝试 Celery 异步
    celery_dispatched = False
    try:
        from tasks.analysis_tasks import generate_decision_report
        generate_decision_report.delay(
            task_id=task_id_str if not db else task_id,
            user_id=user_id,
            project_id=project_id,
            asin_list=asin_list,
        )
        celery_dispatched = True
        logger.info(f"报告生成任务已推入 Celery: task_id={task_id_str}")
    except Exception as e:
        logger.warning(f"Celery 不可用，降级到同步: {e}")

    if not celery_dispatched:
        _execute_report_sync(task_id_str if not db else task_id, user_id, project_id, db)

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id_str,
            "status": "pending",
        },
    })


def _execute_report_sync(task_id, user_id: int, project_id: str, db):
    """同步执行报告生成"""
    try:
        if db:
            _db_update_task(db, task_id, status="processing", started_at=datetime.now())

        from analysis.market_analysis.report_generator import ReportGenerator
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        generator = ReportGenerator(ai_client=ai_client)

        # 收集项目产品数据
        products = []
        keyword = project_id or "analysis"

        if db and project_id:
            # 获取项目关键词
            project_row = db.fetch_one(
                "SELECT keyword FROM sourcing_projects WHERE id = %s AND user_id = %s",
                (project_id, user_id)
            )
            if project_row and project_row.get("keyword"):
                keyword = project_row["keyword"]

            # 获取未过滤的产品数据
            product_rows = db.fetch_all("""
                SELECT asin, title, brand, main_image_url, price_current,
                       fulfillment_type, rating, review_count, est_sales_30d,
                       cvr_30d, bsr_rank, bsr_category
                FROM project_products
                WHERE project_id = %s AND is_filtered = 0
                ORDER BY bsr_rank ASC
                LIMIT 200
            """, (project_id,))
            for row in product_rows:
                products.append({
                    "asin": row.get("asin", ""),
                    "title": row.get("title", ""),
                    "brand": row.get("brand", ""),
                    "main_image": row.get("main_image_url", ""),
                    "price": float(row["price_current"]) if row.get("price_current") else 0,
                    "fulfillment_type": row.get("fulfillment_type", ""),
                    "rating": float(row["rating"]) if row.get("rating") else 0,
                    "review_count": int(row["review_count"]) if row.get("review_count") else 0,
                    "estimated_monthly_sales": int(row["est_sales_30d"]) if row.get("est_sales_30d") else 0,
                    "bsr": int(row["bsr_rank"]) if row.get("bsr_rank") else 0,
                    "category": row.get("bsr_category", ""),
                })

        # 收集已完成的分析数据
        review_analyses = {}
        detail_analyses = {}

        if db:
            completed_tasks = db.fetch_all("""
                SELECT task_type, asin, result_data
                FROM analysis_tasks
                WHERE user_id = %s AND status = 'completed'
                AND task_type IN ('reviews', 'visual')
            """, (user_id,))
            for t in completed_tasks:
                asin = t.get("asin", "")
                result = t.get("result_data")
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        result = {}
                if t["task_type"] == "reviews" and result:
                    review_analyses[asin] = result
                elif t["task_type"] == "visual" and result:
                    detail_analyses[asin] = result
        else:
            for t in _mem_tasks.values():
                if t["user_id"] == user_id and t.get("status") == "completed":
                    asin = t.get("asin", "")
                    if t["task_type"] == "reviews" and t.get("result_data"):
                        review_analyses[asin] = t["result_data"]
                    elif t["task_type"] == "visual" and t.get("result_data"):
                        detail_analyses[asin] = t["result_data"]

        # 收集利润计算数据
        profit_results = []
        if db:
            profit_rows = db.fetch_all("""
                SELECT asin, selling_price, sourcing_cost, net_profit, net_margin, roi
                FROM profit_calculations
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 50
            """, (user_id,))
            for row in profit_rows:
                profit_results.append({
                    "asin": row.get("asin", ""),
                    "selling_price": float(row["selling_price"]) if row.get("selling_price") else 0,
                    "profit": {
                        "profit_per_unit_usd": float(row["net_profit"]) if row.get("net_profit") else 0,
                        "profit_margin": f"{float(row['net_margin'])*100:.1f}%" if row.get("net_margin") else "0%",
                        "roi": f"{float(row['roi'])*100:.1f}%" if row.get("roi") else "0%",
                    },
                })

        # 简单的类目分析（基于已有产品数据生成）
        category_analysis = {}
        if products:
            prices = [p["price"] for p in products if p.get("price")]
            ratings = [p["rating"] for p in products if p.get("rating")]
            reviews = [p["review_count"] for p in products if p.get("review_count")]
            sales = [p["estimated_monthly_sales"] for p in products if p.get("estimated_monthly_sales")]
            avg_price = sum(prices) / len(prices) if prices else 0
            total_sales = sum(sales)
            category_analysis = {
                "market_size": {
                    "estimated_monthly_gmv": round(total_sales * avg_price, 2),
                    "estimated_monthly_sales": total_sales,
                    "product_count": len(products),
                },
                "competition": {
                    "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                    "avg_reviews": round(sum(reviews) / len(reviews)) if reviews else 0,
                    "avg_price": round(avg_price, 2),
                },
                "pricing": {
                    "min_price": round(min(prices), 2) if prices else 0,
                    "max_price": round(max(prices), 2) if prices else 0,
                    "avg_price": round(avg_price, 2),
                },
            }

        report_path = generator.generate(
            keyword=keyword,
            products=products,
            category_analysis=category_analysis,
            profit_results=profit_results,
            review_analyses=review_analyses,
            detail_analyses=detail_analyses,
            output_dir="reports",
        )

        if db:
            _db_update_task(db, task_id,
                            status="completed",
                            report_url=report_path,
                            completed_at=datetime.now())
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)]["status"] = "completed"
            _mem_tasks[str(task_id)]["report_url"] = report_path

    except Exception as e:
        if db:
            _db_update_task(db, task_id, status="failed", error_message=str(e))
        elif str(task_id) in _mem_tasks:
            _mem_tasks[str(task_id)]["status"] = "failed"
            _mem_tasks[str(task_id)]["error_message"] = str(e)
        logger.error(f"报告生成失败: {e}")


# ============================================================
# 市场分析数据 API（供 market_analysis.html 调用）
# ============================================================

@analysis_bp.route("/market", methods=["GET"])
@login_required
def get_market_data(current_user):
    """
    获取市场分析数据

    查询参数:
        keyword: str - 搜索关键词
        marketplace: str - 站点代码 (US/UK/DE/JP)
    """
    keyword = request.args.get("keyword", "").strip()
    marketplace = request.args.get("marketplace", "US").strip()

    if not keyword:
        return jsonify({"success": False, "error": "请提供关键词"}), 400

    user_id = current_user["user_id"]

    try:
        # 尝试从数据库获取已有分析数据
        db = _get_db()
        cached = None
        if db:
            cached = db.fetch_one("""
                SELECT result_data FROM analysis_tasks
                WHERE user_id = %s AND task_type = 'report'
                AND asin = %s AND status = 'completed'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, f"market_{keyword}_{marketplace}"))

        if cached and cached.get("result_data"):
            result = cached["result_data"]
            if isinstance(result, str):
                result = json.loads(result)
            return jsonify({"success": True, "data": result})

        # 实时计算市场数据
        market_data = _compute_market_metrics(keyword, marketplace, user_id, db)

        return jsonify({"success": True, "data": market_data})

    except Exception as e:
        logger.error(f"市场分析失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _compute_market_metrics(keyword: str, marketplace: str, user_id: int, db) -> dict:
    """计算市场指标"""
    # 从项目产品数据中聚合
    products = []
    if db:
        rows = db.fetch_all("""
            SELECT pp.price_current, pp.rating, pp.review_count,
                   pp.est_sales_30d, pp.brand, pp.bsr_rank
            FROM project_products pp
            JOIN sourcing_projects sp ON pp.project_id = sp.id
            WHERE sp.user_id = %s AND sp.keyword LIKE %s
            AND pp.is_filtered = 0
            ORDER BY pp.bsr_rank ASC
            LIMIT 200
        """, (user_id, f"%{keyword}%"))
        products = rows

    if not products:
        # 返回空数据结构，前端会显示"暂无数据"
        return {
            "gmv_estimate": None,
            "seller_count": 0,
            "cr3": None,
            "new_product_ratio": None,
            "avg_price": None,
            "avg_rating": None,
            "avg_reviews": None,
            "price_distribution": [],
            "concentration": [],
            "ai_summary": "暂无足够数据进行市场分析。请先创建选品项目并完成数据抓取。",
            "has_data": False,
        }

    # 计算指标
    prices = [float(p["price_current"]) for p in products if p.get("price_current")]
    ratings = [float(p["rating"]) for p in products if p.get("rating")]
    reviews = [int(p["review_count"]) for p in products if p.get("review_count")]
    sales = [int(p["est_sales_30d"]) for p in products if p.get("est_sales_30d")]

    total_sales = sum(sales) if sales else 0
    avg_price = sum(prices) / len(prices) if prices else 0
    gmv = total_sales * avg_price

    # CR3 - 前3名市场集中度
    brands = {}
    for p in products:
        brand = p.get("brand", "Unknown") or "Unknown"
        brand_sales = int(p.get("est_sales_30d", 0) or 0)
        brands[brand] = brands.get(brand, 0) + brand_sales
    sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)
    top3_sales = sum(s for _, s in sorted_brands[:3])
    cr3 = (top3_sales / total_sales * 100) if total_sales > 0 else 0

    # 新品比例（评论数 < 50 的产品）
    new_products = [p for p in products if (p.get("review_count") or 0) < 50]
    new_ratio = len(new_products) / len(products) * 100 if products else 0

    # 价格分布
    price_ranges = [
        {"range": "$0-10", "min": 0, "max": 10},
        {"range": "$10-20", "min": 10, "max": 20},
        {"range": "$20-30", "min": 20, "max": 30},
        {"range": "$30-50", "min": 30, "max": 50},
        {"range": "$50-100", "min": 50, "max": 100},
        {"range": "$100+", "min": 100, "max": 999999},
    ]
    price_distribution = []
    for pr in price_ranges:
        count = len([p for p in prices if pr["min"] <= p < pr["max"]])
        price_distribution.append({"range": pr["range"], "count": count})

    # 品牌集中度（前10）
    concentration = [
        {"brand": brand, "sales": sales_val}
        for brand, sales_val in sorted_brands[:10]
    ]

    # AI 摘要
    ai_summary = _generate_market_summary(
        keyword, len(products), gmv, cr3, new_ratio, avg_price
    )

    return {
        "gmv_estimate": round(gmv, 2),
        "seller_count": len(set(p.get("brand", "") for p in products)),
        "cr3": round(cr3, 1),
        "new_product_ratio": round(new_ratio, 1),
        "avg_price": round(avg_price, 2),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "avg_reviews": round(sum(reviews) / len(reviews)) if reviews else None,
        "price_distribution": price_distribution,
        "concentration": concentration,
        "ai_summary": ai_summary,
        "has_data": True,
    }


def _generate_market_summary(keyword: str, product_count: int, gmv: float,
                              cr3: float, new_ratio: float, avg_price: float) -> str:
    """生成市场分析 AI 摘要"""
    # 竞争程度判断
    if cr3 > 60:
        competition = "high concentration"
    elif cr3 > 30:
        competition = "moderate competition"
    else:
        competition = "fragmented market"

    gmv_str = f"${gmv / 1_000_000:.1f}M" if gmv >= 1_000_000 else f"${gmv / 1_000:.1f}K"

    return (
        f"Based on the analysis of {product_count} products for \"{keyword}\": "
        f"The market shows {competition} with a CR3 of {cr3:.1f}%, "
        f"indicating {'limited room' if cr3 > 60 else 'room'} for new entrants. "
        f"Monthly GMV is estimated at {gmv_str} with an average selling price of ${avg_price:.2f}. "
        f"The new product ratio of {new_ratio:.1f}% suggests "
        f"{'active innovation' if new_ratio > 15 else 'a mature category'} in this space."
    )


# ============================================================
# 报告数据 API（供 report.html 调用）
# ============================================================

@analysis_bp.route("/report/<project_id>", methods=["GET"])
@login_required
def get_report_data(current_user, project_id):
    """获取项目的综合报告数据"""
    user_id = current_user["user_id"]
    db = _get_db()

    # 收集该项目的所有分析结果
    report_data = {
        "project_id": project_id,
        "scores": {},
        "executive_summary": "",
        "recommendations": {"go": [], "caution": [], "stop": []},
    }

    visual_results = []
    review_results = []

    if db:
        # 验证项目归属
        project = db.fetch_one(
            "SELECT * FROM sourcing_projects WHERE id = %s AND user_id = %s",
            (project_id, user_id)
        )
        if not project:
            return jsonify({"success": False, "error": "项目不存在"}), 404

        # 获取所有已完成的分析任务
        tasks = db.fetch_all("""
            SELECT task_type, asin, result_data, risk_score,
                   visual_usps, pain_points
            FROM analysis_tasks
            WHERE user_id = %s AND project_id = %s AND status = 'completed'
        """, (user_id, project_id))

        for t in tasks:
            result = t.get("result_data")
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    result = {}
            if t["task_type"] == "visual" and result:
                visual_results.append(result)
            elif t["task_type"] == "reviews" and result:
                review_results.append(result)

        # 获取利润计算数据
        profit_data = db.fetch_all("""
            SELECT net_margin, roi, net_profit
            FROM profit_calculations
            WHERE user_id = %s
            ORDER BY created_at DESC LIMIT 10
        """, (user_id,))

        # 获取产品统计
        product_stats = db.fetch_one("""
            SELECT COUNT(*) as total,
                   AVG(rating) as avg_rating,
                   AVG(price_current) as avg_price,
                   AVG(review_count) as avg_reviews
            FROM project_products
            WHERE project_id = %s AND is_filtered = 0
        """, (project_id,))
    else:
        profit_data = []
        product_stats = {"total": 0, "avg_rating": 0, "avg_price": 0, "avg_reviews": 0}

    # 计算评分
    risk_scores = [r.get("assessment", {}).get("overall_score", 50)
                   for r in visual_results if r.get("assessment")]
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 50

    profit_margins = [float(p["net_margin"]) * 100 for p in profit_data if p.get("net_margin")]
    avg_margin = sum(profit_margins) / len(profit_margins) if profit_margins else 50

    scores = {
        "overall": min(100, max(0, int((avg_risk + avg_margin + 50) / 3))),
        "market": min(100, max(0, int(avg_risk * 1.1))) if risk_scores else None,
        "profit": min(100, max(0, int(avg_margin * 1.5))) if profit_margins else None,
        "competition": min(100, max(0, int(100 - avg_risk * 0.5))) if risk_scores else None,
        "risk": min(100, max(0, int(avg_risk))) if risk_scores else None,
    }
    report_data["scores"] = scores

    # 生成建议
    go_reasons = []
    caution_reasons = []
    stop_reasons = []

    if product_stats and product_stats.get("total"):
        total = product_stats["total"]
        if total > 20:
            go_reasons.append(f"Active market with {total} competing products")
        if product_stats.get("avg_rating") and float(product_stats["avg_rating"]) < 4.0:
            go_reasons.append("Average rating below 4.0 indicates room for quality improvement")

    if review_results:
        pain_count = sum(len(r.get("pain_points", [])) for r in review_results)
        if pain_count > 3:
            go_reasons.append(f"{pain_count} customer pain points identified for product differentiation")

    if avg_margin > 25:
        go_reasons.append(f"Healthy profit margins ({avg_margin:.0f}%) achievable")
    elif avg_margin > 10:
        caution_reasons.append(f"Moderate profit margins ({avg_margin:.0f}%) - optimize costs")
    elif profit_margins:
        stop_reasons.append(f"Low profit margins ({avg_margin:.0f}%) may not be sustainable")

    if avg_risk > 70:
        caution_reasons.append("High overall risk score - proceed with caution")

    report_data["recommendations"] = {
        "go": go_reasons or ["Market analysis data is being collected"],
        "caution": caution_reasons or ["Continue monitoring competitor activity"],
        "stop": stop_reasons or ["No critical blockers identified"],
    }

    # 生成摘要
    if visual_results or review_results:
        report_data["executive_summary"] = (
            f"Analysis based on {len(visual_results)} visual assessments and "
            f"{len(review_results)} review analyses. "
            f"Overall score: {scores['overall']}/100. "
            f"{'Strong opportunity identified.' if scores['overall'] > 65 else 'Further research recommended.'}"
        )
    else:
        report_data["executive_summary"] = (
            "Report data is being compiled. Complete visual and review analyses "
            "for comprehensive insights."
        )

    report_data["has_data"] = bool(visual_results or review_results or profit_data)

    return jsonify({"success": True, "data": report_data})


# ============================================================
# 单个产品详情 + 风险分析 (供 product_analysis.html 使用)
# ============================================================

@analysis_bp.route("/product/<asin>", methods=["GET"])
@login_required
def get_product_detail(current_user, asin):
    """获取单个产品的详情数据和风险分析结果"""
    user_id = current_user["user_id"]

    product_data = {
        "asin": asin,
        "title": None,
        "image_url": None,
        "price": None,
        "rating": None,
        "review_count": None,
        "bsr": None,
        "est_sales_30d": None,
        "fulfillment": None,
        "brand": None,
        "category": None,
        "risk_scores": None,
        "risk_assessment": None,
    }

    db = _get_db()
    if db:
        # 从 project_products 表获取产品基本信息
        row = db.fetch_one("""
            SELECT pp.asin, pp.title, pp.image_url, pp.price_current AS price,
                   pp.rating, pp.review_count, pp.bsr_current AS bsr,
                   pp.est_sales_30d, pp.fulfillment_type AS fulfillment,
                   pp.brand, pp.category_name AS category
            FROM project_products pp
            JOIN sourcing_projects sp ON pp.project_id = sp.id
            WHERE pp.asin = %s AND sp.user_id = %s
            ORDER BY pp.created_at DESC LIMIT 1
        """, (asin, user_id))

        if row:
            for key in product_data:
                if key in row and row[key] is not None:
                    product_data[key] = row[key]

        # 从已完成的分析任务中获取风险评分
        visual_task = db.fetch_one("""
            SELECT result FROM analysis_tasks
            WHERE asin = %s AND user_id = %s AND task_type = 'visual'
                  AND status = 'completed' AND result IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        """, (asin, user_id))

        if visual_task and visual_task.get("result"):
            try:
                result = visual_task["result"]
                if isinstance(result, str):
                    result = json.loads(result)
                # 提取风险评分
                if result.get("risk_scores"):
                    product_data["risk_scores"] = result["risk_scores"]
                elif result.get("assessment", {}).get("risk_scores"):
                    product_data["risk_scores"] = result["assessment"]["risk_scores"]
                # 提取 AI 风险评估
                if result.get("risk_assessment"):
                    product_data["risk_assessment"] = result["risk_assessment"]
            except (json.JSONDecodeError, TypeError):
                pass

    # 如果没有风险评分，尝试用 risk_analyzer 实时计算
    if not product_data["risk_scores"] and product_data["title"]:
        try:
            from analysis.risk_analyzer import RiskAnalyzer
            analyzer = RiskAnalyzer()
            risk_result = analyzer.analyze_risks(asin, product_data["title"], {
                "price": product_data.get("price"),
                "rating": product_data.get("rating"),
                "review_count": product_data.get("review_count"),
                "bsr": product_data.get("bsr"),
            })
            if risk_result and risk_result.get("scores"):
                product_data["risk_scores"] = risk_result["scores"]
            if risk_result and risk_result.get("assessment"):
                product_data["risk_assessment"] = {
                    "saturation": risk_result["assessment"].get("market_saturation", "N/A"),
                    "barrier": risk_result["assessment"].get("entry_barrier", "N/A"),
                    "sustainability": risk_result["assessment"].get("profit_sustainability", "N/A"),
                    "ip_risk": risk_result["assessment"].get("ip_risk", "N/A"),
                    "recommendation": risk_result["assessment"].get("recommendation", "N/A"),
                }
        except Exception as e:
            logger.warning(f"实时风险分析失败: {e}")

    return jsonify({"success": True, "data": product_data})
