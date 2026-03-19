"""
产品洞察 API 路由
整合 BSR 追踪、竞品发现、评论情感可视化、AI 选品决策引擎
"""

from flask import Blueprint, request, jsonify
from loguru import logger

product_insight_bp = Blueprint("product_insight", __name__, url_prefix="/api/v1/insights")


# ==================================================================
# BSR 历史追踪 API
# ==================================================================
@product_insight_bp.route("/bsr/record", methods=["POST"])
def record_bsr_snapshot():
    """记录 BSR 快照"""
    data = request.get_json(force=True)
    asin = data.get("asin", "")
    marketplace = data.get("marketplace", "US")

    if not asin:
        return jsonify({"error": "asin is required"}), 400

    try:
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        snapshot = tracker.record_snapshot(
            asin=asin,
            marketplace=marketplace,
            bsr_rank=data.get("bsr_rank"),
            price=data.get("price"),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            est_sales=data.get("est_sales"),
        )
        return jsonify({"success": True, "snapshot": snapshot})
    except Exception as e:
        logger.error(f"BSR 快照记录失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/bsr/history/<asin>", methods=["GET"])
def get_bsr_history(asin):
    """获取 BSR 历史数据"""
    days = request.args.get("days", 90, type=int)
    marketplace = request.args.get("marketplace", "US")

    try:
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        history = tracker.get_history(asin=asin, marketplace=marketplace, days=days)
        return jsonify({"success": True, "data": history})
    except Exception as e:
        logger.error(f"BSR 历史查询失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/bsr/trend/<asin>", methods=["GET"])
def get_bsr_trend_analysis(asin):
    """获取 BSR 趋势分析"""
    marketplace = request.args.get("marketplace", "US")

    try:
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        trend = tracker.analyze_trend(asin=asin, marketplace=marketplace)
        return jsonify({"success": True, "data": trend})
    except Exception as e:
        logger.error(f"BSR 趋势分析失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/bsr/compare", methods=["POST"])
def compare_bsr():
    """对比多个产品的 BSR"""
    data = request.get_json(force=True)
    asins = data.get("asins", [])
    marketplace = data.get("marketplace", "US")

    if not asins or len(asins) < 2:
        return jsonify({"error": "至少需要 2 个 ASIN"}), 400

    try:
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        comparison = tracker.compare_products(asins=asins, marketplace=marketplace)
        return jsonify({"success": True, "data": comparison})
    except Exception as e:
        logger.error(f"BSR 对比失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================================================================
# 竞品发现 API
# ==================================================================
@product_insight_bp.route("/competitors/find", methods=["POST"])
def find_competitors():
    """发现竞品"""
    data = request.get_json(force=True)
    product = data.get("product", {})
    marketplace = data.get("marketplace", "US")
    max_competitors = data.get("max_competitors", 10)

    if not product.get("asin") and not product.get("title"):
        return jsonify({"error": "product.asin or product.title is required"}), 400

    try:
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        competitors = finder.find_competitors(
            product=product,
            marketplace=marketplace,
            max_competitors=max_competitors,
        )
        return jsonify({"success": True, "data": competitors})
    except Exception as e:
        logger.error(f"竞品发现失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/competitors/analyze", methods=["POST"])
def analyze_competitive_landscape():
    """分析竞争格局"""
    data = request.get_json(force=True)
    products = data.get("products", [])

    if len(products) < 2:
        return jsonify({"error": "至少需要 2 个产品"}), 400

    try:
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        landscape = finder.analyze_landscape(products=products)
        return jsonify({"success": True, "data": landscape})
    except Exception as e:
        logger.error(f"竞争格局分析失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/competitors/gaps", methods=["POST"])
def find_market_gaps():
    """发现市场空白"""
    data = request.get_json(force=True)
    products = data.get("products", [])

    if not products:
        return jsonify({"error": "products is required"}), 400

    try:
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        gaps = finder.find_market_gaps(products=products)
        return jsonify({"success": True, "data": gaps})
    except Exception as e:
        logger.error(f"市场空白分析失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================================================================
# 评论情感可视化 API
# ==================================================================
@product_insight_bp.route("/sentiment/analyze", methods=["POST"])
def analyze_sentiment():
    """分析评论情感"""
    data = request.get_json(force=True)
    reviews = data.get("reviews", [])

    if not reviews:
        return jsonify({"error": "reviews is required"}), 400

    try:
        from analysis.sentiment_visualizer import SentimentVisualizer
        visualizer = SentimentVisualizer()
        result = visualizer.analyze_reviews(reviews=reviews)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/sentiment/wordcloud", methods=["POST"])
def generate_wordcloud():
    """生成词云数据"""
    data = request.get_json(force=True)
    reviews = data.get("reviews", [])
    max_words = data.get("max_words", 100)

    if not reviews:
        return jsonify({"error": "reviews is required"}), 400

    try:
        from analysis.sentiment_visualizer import SentimentVisualizer
        visualizer = SentimentVisualizer()
        wordcloud = visualizer.generate_word_cloud(reviews=reviews, max_words=max_words)
        return jsonify({"success": True, "data": wordcloud})
    except Exception as e:
        logger.error(f"词云生成失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/sentiment/tags", methods=["POST"])
def extract_review_tags():
    """提取评论标签"""
    data = request.get_json(force=True)
    reviews = data.get("reviews", [])

    if not reviews:
        return jsonify({"error": "reviews is required"}), 400

    try:
        from analysis.sentiment_visualizer import SentimentVisualizer
        visualizer = SentimentVisualizer()
        tags = visualizer.extract_tags(reviews=reviews)
        return jsonify({"success": True, "data": tags})
    except Exception as e:
        logger.error(f"标签提取失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================================================================
# AI 选品决策引擎 API
# ==================================================================
@product_insight_bp.route("/decision/evaluate", methods=["POST"])
def evaluate_product_decision():
    """评估单个产品的选品决策"""
    data = request.get_json(force=True)
    product_data = data.get("product", {})
    market_data = data.get("market", {})
    profit_data = data.get("profit", {})
    review_data = data.get("review", {})
    competitor_data = data.get("competitor", {})

    if not product_data:
        return jsonify({"error": "product data is required"}), 400

    try:
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine()
        result = engine.evaluate_product(
            product_data=product_data,
            market_data=market_data,
            profit_data=profit_data,
            review_data=review_data,
            competitor_data=competitor_data,
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"选品决策评估失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/decision/batch", methods=["POST"])
def batch_evaluate_decision():
    """批量评估产品选品决策"""
    data = request.get_json(force=True)
    products = data.get("products", [])
    market_data = data.get("market", {})
    profit_results = data.get("profit_results", [])
    competitor_data = data.get("competitor", {})

    if not products:
        return jsonify({"error": "products is required"}), 400

    try:
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine()
        result = engine.batch_evaluate(
            products=products,
            market_data=market_data,
            profit_results=profit_results,
            competitor_data=competitor_data,
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"批量选品决策评估失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================================================================
# 增强看板 API
# ==================================================================
@product_insight_bp.route("/dashboard/full", methods=["GET"])
def get_full_dashboard():
    """获取完整看板数据"""
    project_id = request.args.get("project_id", type=int)

    try:
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        dashboard = analytics.get_full_dashboard(project_id=project_id)
        return jsonify({"success": True, "data": dashboard})
    except Exception as e:
        logger.error(f"看板数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/dashboard/funnel", methods=["GET"])
def get_selection_funnel():
    """获取选品漏斗数据"""
    project_id = request.args.get("project_id", type=int)

    try:
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        funnel = analytics.get_selection_funnel(project_id=project_id)
        return jsonify({"success": True, "data": funnel})
    except Exception as e:
        logger.error(f"漏斗数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/dashboard/kpi", methods=["GET"])
def get_kpi_cards():
    """获取 KPI 卡片数据"""
    try:
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        cards = analytics.get_kpi_cards()
        return jsonify({"success": True, "data": cards})
    except Exception as e:
        logger.error(f"KPI 数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/dashboard/trend", methods=["GET"])
def get_activity_trend():
    """获取活动趋势数据"""
    days = request.args.get("days", 30, type=int)

    try:
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        trend = analytics.get_activity_trend(days=days)
        return jsonify({"success": True, "data": trend})
    except Exception as e:
        logger.error(f"趋势数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500


@product_insight_bp.route("/dashboard/profit-distribution", methods=["GET"])
def get_profit_distribution():
    """获取利润分布数据"""
    try:
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        distribution = analytics.get_profit_distribution()
        return jsonify({"success": True, "data": distribution})
    except Exception as e:
        logger.error(f"利润分布数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500
