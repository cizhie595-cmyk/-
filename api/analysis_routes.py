"""
深度分析 API 路由
对应 PRD 8.4 - Analysis

端点:
    POST /api/v1/analysis/visual              发起视觉语义分析
    POST /api/v1/analysis/reviews             发起评论深度挖掘
    GET  /api/v1/analysis/{task_id}/result    获取分析结果
    POST /api/v1/analysis/report/generate     生成综合决策报告
"""

import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/v1/analysis")

# 内存存储（生产环境应替换为数据库）
_analysis_tasks = {}


# ============================================================
# 视觉语义分析
# ============================================================

@analysis_bp.route("/visual", methods=["POST"])
@login_required
@quota_required("analysis")
def visual_analysis(current_user):
    """
    发起视觉语义分析

    请求体:
        asin: str - 目标 ASIN
        dimensions: list[str] - 分析维度
            可选: ["listing_quality", "review_health", "fulfillment", "variants", "opportunities"]
    """
    data = request.get_json() or {}

    asin = data.get("asin", "").strip()
    if not asin:
        return jsonify({"success": False, "error": "请提供 ASIN"}), 400

    dimensions = data.get("dimensions", [
        "listing_quality", "review_health", "fulfillment", "variants", "opportunities"
    ])

    task_id = str(uuid.uuid4())[:12]
    task = {
        "task_id": task_id,
        "task_type": "visual",
        "user_id": current_user["user_id"],
        "asin": asin,
        "dimensions": dimensions,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    _analysis_tasks[task_id] = task

    # 异步执行分析（生产环境应推入 Celery 队列）
    _execute_visual_analysis(task, current_user["user_id"])

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": task["status"],
        },
    })


def _execute_visual_analysis(task: dict, user_id: int):
    """执行视觉语义分析"""
    try:
        task["status"] = "processing"
        task["started_at"] = datetime.now().isoformat()

        asin = task["asin"]

        # 使用 Amazon 深度分析器
        from scrapers.amazon.deep_crawler import AmazonDeepCrawler
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        crawler = AmazonDeepCrawler(ai_client=ai_client)

        try:
            result = crawler.deep_analyze(asin)
        finally:
            crawler.close()

        if result:
            task["status"] = "completed"
            task["result_data"] = result
            task["visual_usps"] = result.get("opportunities", [])
            task["trust_signals"] = result.get("assessment", {}).get("listing_quality", {})
            task["risk_score"] = result.get("assessment", {}).get("overall_score")
            task["completed_at"] = datetime.now().isoformat()
        else:
            task["status"] = "failed"
            task["error_message"] = "分析未返回结果"

    except Exception as e:
        task["status"] = "failed"
        task["error_message"] = str(e)
        logger.error(f"视觉分析任务失败: {e}")


# ============================================================
# 评论深度挖掘
# ============================================================

@analysis_bp.route("/reviews", methods=["POST"])
@login_required
@quota_required("analysis")
def review_analysis(current_user):
    """
    发起评论深度挖掘

    请求体:
        asin: str - 目标 ASIN
        review_count: int - 抓取评论数量 (默认 500)
    """
    data = request.get_json() or {}

    asin = data.get("asin", "").strip()
    if not asin:
        return jsonify({"success": False, "error": "请提供 ASIN"}), 400

    review_count = data.get("review_count", 500)

    task_id = str(uuid.uuid4())[:12]
    task = {
        "task_id": task_id,
        "task_type": "reviews",
        "user_id": current_user["user_id"],
        "asin": asin,
        "review_count": review_count,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    _analysis_tasks[task_id] = task

    # 异步执行分析
    _execute_review_analysis(task, current_user["user_id"])

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": task["status"],
        },
    })


def _execute_review_analysis(task: dict, user_id: int):
    """执行评论深度挖掘"""
    try:
        task["status"] = "processing"
        task["started_at"] = datetime.now().isoformat()

        asin = task["asin"]
        max_reviews = task.get("review_count", 500)

        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)

        # 爬取评论
        review_crawler = AmazonReviewCrawler()
        try:
            reviews = review_crawler.crawl_reviews(asin, max_reviews=max_reviews)
            suspicious = review_crawler._detect_fake_reviews(reviews)
        finally:
            review_crawler.close()

        if not reviews:
            task["status"] = "completed"
            task["result_data"] = {"message": "未找到评论数据"}
            task["completed_at"] = datetime.now().isoformat()
            return

        # AI 分析评论
        analyzer = ReviewAnalyzer(ai_client=ai_client)
        analysis = analyzer.analyze(reviews, asin)

        task["status"] = "completed"
        task["result_data"] = analysis
        task["pain_points"] = analysis.get("pain_points", [])
        task["buyer_persona"] = analysis.get("buyer_persona", "")
        task["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        task["status"] = "failed"
        task["error_message"] = str(e)
        logger.error(f"评论分析任务失败: {e}")


# ============================================================
# 获取分析结果
# ============================================================

@analysis_bp.route("/<task_id>/result", methods=["GET"])
@login_required
def get_analysis_result(current_user, task_id):
    """获取分析结果"""
    task = _analysis_tasks.get(task_id)
    if not task or task["user_id"] != current_user["user_id"]:
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
    """
    生成综合决策报告

    请求体:
        project_id: str - 项目ID
        asin_list: list[str] - 要包含在报告中的 ASIN 列表
        include_sections: list[str] - 报告章节
            可选: ["market_overview", "competitor_analysis", "profit_analysis",
                   "risk_assessment", "recommendation"]
    """
    data = request.get_json() or {}

    project_id = data.get("project_id")
    asin_list = data.get("asin_list", [])
    include_sections = data.get("include_sections", [
        "market_overview", "competitor_analysis", "profit_analysis",
        "risk_assessment", "recommendation"
    ])

    if not project_id and not asin_list:
        return jsonify({"success": False, "error": "请提供项目ID或ASIN列表"}), 400

    task_id = str(uuid.uuid4())[:12]
    task = {
        "task_id": task_id,
        "task_type": "report",
        "user_id": current_user["user_id"],
        "project_id": project_id,
        "asin_list": asin_list,
        "include_sections": include_sections,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    _analysis_tasks[task_id] = task

    # 异步执行报告生成
    _execute_report_generation(task, current_user["user_id"])

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": task["status"],
        },
    })


def _execute_report_generation(task: dict, user_id: int):
    """执行综合报告生成"""
    try:
        task["status"] = "processing"
        task["started_at"] = datetime.now().isoformat()

        from analysis.market_analysis.report_generator import ReportGenerator
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        generator = ReportGenerator(ai_client=ai_client)

        # 收集所有已完成的分析数据
        user_tasks = [
            t for t in _analysis_tasks.values()
            if t["user_id"] == user_id and t["status"] == "completed"
        ]

        review_analyses = {}
        detail_analyses = {}
        for t in user_tasks:
            asin = t.get("asin", "")
            if t["task_type"] == "reviews" and t.get("result_data"):
                review_analyses[asin] = t["result_data"]
            elif t["task_type"] == "visual" and t.get("result_data"):
                detail_analyses[asin] = t["result_data"]

        report_path = generator.generate(
            keyword=task.get("project_id", "analysis"),
            products=[],
            category_analysis={},
            profit_results=[],
            review_analyses=review_analyses,
            detail_analyses=detail_analyses,
            output_dir="reports",
        )

        task["status"] = "completed"
        task["report_url"] = report_path
        task["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        task["status"] = "failed"
        task["error_message"] = str(e)
        logger.error(f"报告生成失败: {e}")
