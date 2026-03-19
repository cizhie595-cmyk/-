"""
关键词研究 API 路由

提供关键词分析、搜索量估算、长尾词挖掘、竞争度评估等端点。
"""

from flask import Blueprint, request, jsonify
from utils.logger import get_logger

logger = get_logger()

keyword_bp = Blueprint("keyword", __name__, url_prefix="/api/v1/keyword")


def _get_researcher():
    """创建 KeywordResearcher 实例"""
    from analysis.keyword_researcher import KeywordResearcher
    return KeywordResearcher()


# ================================================================
# 关键词分析
# ================================================================

@keyword_bp.route("/analyze", methods=["POST"])
def analyze_keyword():
    """分析单个关键词"""
    data = request.get_json() or {}
    keyword = data.get("keyword", "")
    marketplace = data.get("marketplace", "US")

    if not keyword:
        return jsonify({"success": False, "error": "Keyword is required"}), 400

    researcher = _get_researcher()
    result = researcher.analyze_keyword(keyword, marketplace)

    return jsonify({"success": True, "data": result})


@keyword_bp.route("/batch-analyze", methods=["POST"])
def batch_analyze():
    """批量分析关键词"""
    data = request.get_json() or {}
    keywords = data.get("keywords", [])
    marketplace = data.get("marketplace", "US")

    if not keywords:
        return jsonify({"success": False, "error": "Keywords list is required"}), 400

    researcher = _get_researcher()
    results = researcher.batch_analyze(keywords, marketplace)

    return jsonify({"success": True, "data": results, "count": len(results)})


# ================================================================
# 关键词建议
# ================================================================

@keyword_bp.route("/suggest", methods=["POST"])
def suggest_keywords():
    """获取关键词建议"""
    data = request.get_json() or {}
    seed_keyword = data.get("keyword", "")
    marketplace = data.get("marketplace", "US")
    max_results = data.get("max_results", 20)

    if not seed_keyword:
        return jsonify({"success": False, "error": "Seed keyword is required"}), 400

    researcher = _get_researcher()
    suggestions = researcher.suggest_keywords(seed_keyword, marketplace, max_results)

    return jsonify({"success": True, "data": suggestions, "count": len(suggestions)})


# ================================================================
# 长尾词挖掘
# ================================================================

@keyword_bp.route("/long-tail", methods=["POST"])
def find_long_tail():
    """挖掘长尾关键词"""
    data = request.get_json() or {}
    seed_keyword = data.get("keyword", "")
    marketplace = data.get("marketplace", "US")
    max_results = data.get("max_results", 30)

    if not seed_keyword:
        return jsonify({"success": False, "error": "Seed keyword is required"}), 400

    researcher = _get_researcher()
    long_tail = researcher.find_long_tail_keywords(seed_keyword, marketplace, max_results)

    return jsonify({"success": True, "data": long_tail, "count": len(long_tail)})


# ================================================================
# 竞争度评估
# ================================================================

@keyword_bp.route("/competition", methods=["POST"])
def assess_competition():
    """评估关键词竞争度"""
    data = request.get_json() or {}
    keyword = data.get("keyword", "")
    products = data.get("products", [])
    marketplace = data.get("marketplace", "US")

    if not keyword:
        return jsonify({"success": False, "error": "Keyword is required"}), 400

    researcher = _get_researcher()
    result = researcher.assess_competition(keyword, products, marketplace)

    return jsonify({"success": True, "data": result})


# ================================================================
# 关键词评分排名
# ================================================================

@keyword_bp.route("/rank", methods=["POST"])
def rank_keywords():
    """对多个关键词进行评分排名"""
    data = request.get_json() or {}
    keywords = data.get("keywords", [])
    marketplace = data.get("marketplace", "US")

    if not keywords:
        return jsonify({"success": False, "error": "Keywords list is required"}), 400

    researcher = _get_researcher()
    results = researcher.batch_analyze(keywords, marketplace)

    # 按综合得分排序
    results.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

    return jsonify({"success": True, "data": results, "count": len(results)})
