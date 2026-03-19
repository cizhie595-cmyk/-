"""
定价策略优化 API 路由

提供最优定价建议、价格弹性模拟、多策略对比、促销建议等端点。
"""

from flask import Blueprint, request, jsonify
from utils.logger import get_logger

logger = get_logger()

pricing_bp = Blueprint("pricing", __name__, url_prefix="/api/v1/pricing")


def _get_optimizer(marketplace="US", exchange_rate=7.25):
    """创建 PricingOptimizer 实例"""
    from analysis.pricing_optimizer import PricingOptimizer
    return PricingOptimizer(marketplace=marketplace, exchange_rate=exchange_rate)


def _get_db():
    """获取数据库连接"""
    try:
        from database.connection import get_db
        return get_db()
    except Exception:
        return None


def _get_project_products(project_id):
    """从数据库获取项目产品列表"""
    db = _get_db()
    if not db:
        return []
    try:
        cursor = db.execute(
            "SELECT * FROM project_products WHERE project_id = ?",
            (project_id,),
        )
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to get project products: {e}")
        return []


# ================================================================
# 价格分布分析
# ================================================================

@pricing_bp.route("/distribution", methods=["POST"])
def analyze_distribution():
    """分析竞品价格分布"""
    data = request.get_json() or {}
    products = data.get("products", [])
    project_id = data.get("project_id")
    marketplace = data.get("marketplace", "US")

    # 如果传入 project_id，从数据库获取产品
    if project_id and not products:
        products = _get_project_products(project_id)

    if not products:
        return jsonify({"success": False, "error": "Products data is required"}), 400

    optimizer = _get_optimizer(marketplace)
    result = optimizer.analyze_price_distribution(products)

    return jsonify({"success": True, "data": result})


# ================================================================
# 最优定价建议
# ================================================================

@pricing_bp.route("/optimal", methods=["POST"])
def suggest_optimal():
    """获取最优定价建议"""
    data = request.get_json() or {}
    cost_params = data.get("cost_params", {})
    products = data.get("products", [])
    project_id = data.get("project_id")
    target_margin = data.get("target_margin", 0.25)
    marketplace = data.get("marketplace", "US")
    exchange_rate = data.get("exchange_rate", 7.25)

    if project_id and not products:
        products = _get_project_products(project_id)

    if not cost_params:
        return jsonify({"success": False, "error": "Cost parameters are required"}), 400
    if not products:
        return jsonify({"success": False, "error": "Products data is required"}), 400

    optimizer = _get_optimizer(marketplace, exchange_rate)
    result = optimizer.suggest_optimal_price(cost_params, products, target_margin)

    return jsonify({"success": True, "data": result})


# ================================================================
# 价格弹性模拟
# ================================================================

@pricing_bp.route("/elasticity", methods=["POST"])
def simulate_elasticity():
    """模拟价格弹性"""
    data = request.get_json() or {}
    cost_params = data.get("cost_params", {})
    products = data.get("products", [])
    project_id = data.get("project_id")
    marketplace = data.get("marketplace", "US")
    exchange_rate = data.get("exchange_rate", 7.25)
    steps = data.get("steps", 10)

    if project_id and not products:
        products = _get_project_products(project_id)

    if not cost_params or not products:
        return jsonify({"success": False, "error": "Cost parameters and products are required"}), 400

    optimizer = _get_optimizer(marketplace, exchange_rate)
    result = optimizer.simulate_price_elasticity(cost_params, products, steps=steps)

    return jsonify({"success": True, "data": result})


# ================================================================
# 多策略对比
# ================================================================

@pricing_bp.route("/strategies", methods=["POST"])
def compare_strategies():
    """对比多种定价策略"""
    data = request.get_json() or {}
    cost_params = data.get("cost_params", {})
    products = data.get("products", [])
    project_id = data.get("project_id")
    marketplace = data.get("marketplace", "US")
    exchange_rate = data.get("exchange_rate", 7.25)

    if project_id and not products:
        products = _get_project_products(project_id)

    if not cost_params or not products:
        return jsonify({"success": False, "error": "Cost parameters and products are required"}), 400

    optimizer = _get_optimizer(marketplace, exchange_rate)
    result = optimizer.compare_strategies(cost_params, products)

    return jsonify({"success": True, "data": result})


# ================================================================
# 促销定价建议
# ================================================================

@pricing_bp.route("/promotions", methods=["POST"])
def suggest_promotions():
    """获取促销定价建议"""
    data = request.get_json() or {}
    current_price = data.get("current_price", 0)
    cost_params = data.get("cost_params", {})
    products = data.get("products", [])
    project_id = data.get("project_id")
    marketplace = data.get("marketplace", "US")
    exchange_rate = data.get("exchange_rate", 7.25)

    if project_id and not products:
        products = _get_project_products(project_id)

    if not current_price or not cost_params:
        return jsonify({"success": False, "error": "Current price and cost parameters are required"}), 400

    optimizer = _get_optimizer(marketplace, exchange_rate)
    result = optimizer.suggest_promotions(current_price, cost_params, products)

    return jsonify({"success": True, "data": result})
