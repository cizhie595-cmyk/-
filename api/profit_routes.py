"""
利润计算与供应链 API 路由
对应 PRD 8.6 - Profit & Supply Chain

端点:
    POST /api/v1/profit/calculate          计算单品利润
    POST /api/v1/profit/batch              批量利润计算
    POST /api/v1/supply/image-search       以图搜货 (1688)
    POST /api/v1/supply/keyword-search     关键词搜货 (1688)
"""

from flask import Blueprint, request, jsonify

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

profit_bp = Blueprint("profit", __name__, url_prefix="/api/v1")


# ============================================================
# 利润计算
# ============================================================

@profit_bp.route("/profit/calculate", methods=["POST"])
@login_required
def calculate_profit(current_user):
    """
    计算单品利润

    请求体:
        selling_price: float - 售价 (USD)
        sourcing_cost: float - 采购成本 (RMB)
        weight_kg: float - 产品重量 (kg)
        length_cm: float - 长 (cm)
        width_cm: float - 宽 (cm)
        height_cm: float - 高 (cm)
        category: str - 产品类目 (用于计算佣金率)
        marketplace: str - 站点 (US/UK/DE/JP, 默认 US)
        exchange_rate: float - 汇率 (默认 7.25)
        shipping_cost_per_kg: float - 头程运费/kg (默认 40 RMB)
        estimated_cpa: float - 预估 CPA (USD, 默认 0)
        return_rate: float - 退货率 (默认 0.05)
    """
    data = request.get_json() or {}

    selling_price = data.get("selling_price")
    sourcing_cost = data.get("sourcing_cost")

    if not selling_price or not sourcing_cost:
        return jsonify({"success": False, "error": "请提供售价和采购成本"}), 400

    marketplace = data.get("marketplace", "US")

    try:
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

        calculator = AmazonFBAProfitCalculator(
            marketplace=marketplace,
            exchange_rate=data.get("exchange_rate", 7.25),
        )

        params = {
            "selling_price": float(selling_price),
            "sourcing_cost_rmb": float(sourcing_cost),
            "weight_kg": data.get("weight_kg", 0.5),
            "length_cm": data.get("length_cm", 20),
            "width_cm": data.get("width_cm", 15),
            "height_cm": data.get("height_cm", 10),
            "category": data.get("category", "General"),
            "shipping_cost_per_kg": data.get("shipping_cost_per_kg", 40),
            "estimated_cpa": data.get("estimated_cpa", 0),
            "return_rate": data.get("return_rate", 0.05),
        }

        result = calculator.calculate_profit(params)

        return jsonify({
            "success": True,
            "data": result,
        })

    except Exception as e:
        logger.error(f"利润计算失败: {e}")
        return jsonify({"success": False, "error": f"计算失败: {str(e)}"}), 500


@profit_bp.route("/profit/batch", methods=["POST"])
@login_required
def batch_calculate_profit(current_user):
    """
    批量利润计算

    请求体:
        products: list[dict] - 产品列表，每个产品包含 calculate 接口的参数
        marketplace: str - 站点 (默认 US)
        exchange_rate: float - 汇率 (默认 7.25)
    """
    data = request.get_json() or {}
    products = data.get("products", [])

    if not products:
        return jsonify({"success": False, "error": "请提供产品列表"}), 400

    marketplace = data.get("marketplace", "US")

    try:
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

        calculator = AmazonFBAProfitCalculator(
            marketplace=marketplace,
            exchange_rate=data.get("exchange_rate", 7.25),
        )

        results = calculator.batch_calculate(products)

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "total_count": len(results),
            },
        })

    except Exception as e:
        logger.error(f"批量利润计算失败: {e}")
        return jsonify({"success": False, "error": f"计算失败: {str(e)}"}), 500


# ============================================================
# 供应链搜索
# ============================================================

@profit_bp.route("/supply/image-search", methods=["POST"])
@login_required
@quota_required("scrape")
def image_search_1688(current_user):
    """
    以图搜货 (1688)

    请求体:
        image_url: str - 图片 URL
        max_results: int - 最大结果数 (默认 20)
    """
    data = request.get_json() or {}
    image_url = data.get("image_url", "").strip()

    if not image_url:
        return jsonify({"success": False, "error": "请提供图片URL"}), 400

    max_results = data.get("max_results", 20)

    try:
        from scrapers.alibaba1688.source_crawler import Alibaba1688Crawler
        import tempfile
        import requests as req

        # 下载图片到临时文件
        response = req.get(image_url, timeout=30)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        crawler = Alibaba1688Crawler()
        try:
            sources = crawler.search_by_image(tmp_path, max_results=max_results)
        finally:
            crawler.close()

        # 清理临时文件
        import os
        os.unlink(tmp_path)

        return jsonify({
            "success": True,
            "data": {
                "sources": sources,
                "total_count": len(sources),
            },
        })

    except Exception as e:
        logger.error(f"以图搜货失败: {e}")
        return jsonify({"success": False, "error": f"搜索失败: {str(e)}"}), 500


@profit_bp.route("/supply/keyword-search", methods=["POST"])
@login_required
@quota_required("scrape")
def keyword_search_1688(current_user):
    """
    关键词搜货 (1688)

    请求体:
        keyword: str - 搜索关键词
        max_results: int - 最大结果数 (默认 20)
    """
    data = request.get_json() or {}
    keyword = data.get("keyword", "").strip()

    if not keyword:
        return jsonify({"success": False, "error": "请提供搜索关键词"}), 400

    max_results = data.get("max_results", 20)

    try:
        from scrapers.alibaba1688.source_crawler import Alibaba1688Crawler

        crawler = Alibaba1688Crawler()
        try:
            sources = crawler.search_by_keyword(keyword, max_results=max_results)
        finally:
            crawler.close()

        return jsonify({
            "success": True,
            "data": {
                "sources": sources,
                "total_count": len(sources),
            },
        })

    except Exception as e:
        logger.error(f"关键词搜货失败: {e}")
        return jsonify({"success": False, "error": f"搜索失败: {str(e)}"}), 500


# ============================================================
# 利润计算历史
# ============================================================

@profit_bp.route("/profit/save", methods=["POST"])
@login_required
def save_profit_calculation(current_user):
    """
    保存利润计算结果

    请求体:
        asin: str (optional) - ASIN
        selling_price: float - 售价
        sourcing_cost: float - 采购成本 (RMB)
        marketplace: str - 站点
        category: str - 类目
        weight_kg: float - 重量
        exchange_rate: float - 汇率
        net_profit: float - 净利润
        net_margin: float - 利润率
        roi: float - ROI
    """
    data = request.get_json() or {}

    user_id = current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", None)

    record = {
        "user_id": user_id,
        "asin": data.get("asin"),
        "selling_price": data.get("selling_price", 0),
        "sourcing_cost": data.get("sourcing_cost", 0),
        "marketplace": data.get("marketplace", "US"),
        "category": data.get("category", "general"),
        "weight_kg": data.get("weight_kg", 0.5),
        "exchange_rate": data.get("exchange_rate", 7.25),
        "net_profit": data.get("net_profit", 0),
        "net_margin": data.get("net_margin", 0),
        "roi": data.get("roi", 0),
    }

    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO profit_calculations
            (user_id, asin, selling_price, sourcing_cost, net_profit, net_margin, roi)
            VALUES (%(user_id)s, %(asin)s, %(selling_price)s, %(sourcing_cost)s,
                    %(net_profit)s, %(net_margin)s, %(roi)s)
        """, record)
        conn.commit()
        calc_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"success": True, "id": calc_id, "message": "Saved successfully"})

    except Exception as e:
        logger.warning(f"数据库保存失败，使用本地存储: {e}")
        # 降级: 返回成功让前端用 localStorage
        return jsonify({"success": True, "id": None, "message": "Saved (local mode)", "fallback": True})


@profit_bp.route("/profit/history", methods=["GET"])
@login_required
def get_profit_history(current_user):
    """
    获取利润计算历史

    查询参数:
        limit: int - 返回数量 (默认 50)
    """
    user_id = current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", None)
    limit = request.args.get("limit", 50, type=int)

    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, asin, selling_price, sourcing_cost,
                   net_profit, net_margin, roi, created_at
            FROM profit_calculations
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # 序列化 datetime
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()

        return jsonify({"success": True, "data": rows})

    except Exception as e:
        logger.warning(f"获取历史记录失败: {e}")
        return jsonify({"success": True, "data": []})
