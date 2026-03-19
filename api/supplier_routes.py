"""
供应商评分 API 路由

提供供应商评分、批量评分、对比矩阵等端点。
"""

from flask import Blueprint, request, jsonify
from utils.logger import get_logger

logger = get_logger()

supplier_bp = Blueprint("supplier", __name__, url_prefix="/api/v1/supplier")


def _get_scorer():
    """创建 SupplierScorer 实例"""
    from analysis.supplier_scorer import SupplierScorer
    return SupplierScorer()


# ================================================================
# 单个供应商评分
# ================================================================

@supplier_bp.route("/score", methods=["POST"])
def score_supplier():
    """对单个供应商进行综合评分"""
    data = request.get_json() or {}
    supplier = data.get("supplier", {})
    market_avg_price = data.get("market_avg_price", 0)

    if not supplier:
        return jsonify({"success": False, "error": "Supplier data is required"}), 400

    scorer = _get_scorer()
    result = scorer.score_supplier(supplier, market_avg_price)

    return jsonify({"success": True, "data": result})


# ================================================================
# 单维度评分
# ================================================================

@supplier_bp.route("/score/<dimension>", methods=["POST"])
def score_dimension(dimension):
    """对供应商进行单维度评分"""
    data = request.get_json() or {}
    supplier = data.get("supplier", {})

    if not supplier:
        return jsonify({"success": False, "error": "Supplier data is required"}), 400

    scorer = _get_scorer()

    dimension_methods = {
        "credibility": scorer.score_credibility,
        "product_capability": scorer.score_product_capability,
        "service_quality": scorer.score_service_quality,
        "price_competitiveness": lambda s: scorer.score_price_competitiveness(
            s, data.get("market_avg_price", 0)
        ),
        "logistics": scorer.score_logistics,
    }

    if dimension not in dimension_methods:
        return jsonify({
            "success": False,
            "error": f"Invalid dimension: {dimension}. Valid: {list(dimension_methods.keys())}",
        }), 400

    result = dimension_methods[dimension](supplier)

    return jsonify({"success": True, "data": result})


# ================================================================
# 批量评分
# ================================================================

@supplier_bp.route("/score/batch", methods=["POST"])
def batch_score():
    """批量评分多个供应商"""
    data = request.get_json() or {}
    suppliers = data.get("suppliers", [])
    market_avg_price = data.get("market_avg_price", 0)

    if not suppliers:
        return jsonify({"success": False, "error": "Suppliers list is required"}), 400

    scorer = _get_scorer()
    results = scorer.score_multiple_suppliers(suppliers, market_avg_price)

    return jsonify({"success": True, "data": results, "count": len(results)})


# ================================================================
# 对比矩阵
# ================================================================

@supplier_bp.route("/compare", methods=["POST"])
def compare_suppliers():
    """生成供应商对比矩阵"""
    data = request.get_json() or {}
    suppliers = data.get("suppliers", [])
    market_avg_price = data.get("market_avg_price", 0)

    if not suppliers or len(suppliers) < 2:
        return jsonify({
            "success": False,
            "error": "At least 2 suppliers are required for comparison",
        }), 400

    scorer = _get_scorer()
    matrix = scorer.generate_comparison_matrix(suppliers, market_avg_price)

    return jsonify({"success": True, "data": matrix})
