"""
选品项目 API 路由
对应 PRD 8.3 - Sourcing Projects

端点:
    POST   /api/v1/projects/create           创建选品项目
    POST   /api/v1/projects/{id}/scrape      发起数据抓取任务
    GET    /api/v1/projects/{id}/products     获取抓取结果列表
    POST   /api/v1/projects/{id}/filter/ai   AI 智能过滤
    GET    /api/v1/projects                   获取用户的项目列表
    GET    /api/v1/projects/{id}              获取项目详情
    DELETE /api/v1/projects/{id}              删除项目
"""

import os
import json
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

project_bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


# ============================================================
# 内存存储（生产环境应替换为数据库）
# ============================================================
_projects = {}
_project_products = {}
_scrape_tasks = {}


# ============================================================
# 项目管理
# ============================================================

@project_bp.route("/create", methods=["POST"])
@login_required
def create_project(current_user):
    """
    创建选品项目

    请求体:
        name: str - 项目名称
        marketplace_id: str - 站点ID (如 ATVPDKIKX0DER)
        keyword: str - 搜索关键词 (与 file_upload_id 二选一)
        file_upload_id: str - 上传文件ID (与 keyword 二选一)
        scrape_depth: int - 抓取深度 (50/100/200)
    """
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "项目名称不能为空"}), 400

    keyword = data.get("keyword", "").strip()
    file_upload_id = data.get("file_upload_id", "").strip()
    if not keyword and not file_upload_id:
        return jsonify({"success": False, "error": "请提供搜索关键词或上传数据文件"}), 400

    project_id = str(uuid.uuid4())[:8]
    project = {
        "project_id": project_id,
        "user_id": current_user["user_id"],
        "name": name,
        "marketplace_id": data.get("marketplace_id", "ATVPDKIKX0DER"),
        "keyword": keyword,
        "file_upload_id": file_upload_id,
        "scrape_depth": data.get("scrape_depth", 100),
        "status": "created",
        "product_count": 0,
        "filtered_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _projects[project_id] = project

    logger.info(f"用户 {current_user['user_id']} 创建选品项目: {name} ({project_id})")

    return jsonify({
        "success": True,
        "data": {"project_id": project_id},
    }), 201


@project_bp.route("", methods=["GET"])
@login_required
def list_projects(current_user):
    """获取用户的项目列表"""
    user_id = current_user["user_id"]
    user_projects = [
        p for p in _projects.values()
        if p["user_id"] == user_id
    ]
    user_projects.sort(key=lambda x: x["created_at"], reverse=True)

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "success": True,
        "data": {
            "projects": user_projects[start:end],
            "total_count": len(user_projects),
            "page": page,
            "page_size": page_size,
        },
    })


@project_bp.route("/<project_id>", methods=["GET"])
@login_required
def get_project(current_user, project_id):
    """获取项目详情"""
    project = _projects.get(project_id)
    if not project or project["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    return jsonify({"success": True, "data": project})


@project_bp.route("/<project_id>", methods=["DELETE"])
@login_required
def delete_project(current_user, project_id):
    """删除项目"""
    project = _projects.get(project_id)
    if not project or project["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    del _projects[project_id]
    _project_products.pop(project_id, None)

    return jsonify({"success": True, "message": "项目已删除"})


# ============================================================
# 数据抓取
# ============================================================

@project_bp.route("/<project_id>/scrape", methods=["POST"])
@login_required
@quota_required("scrape")
def scrape_project(current_user, project_id):
    """
    发起数据抓取任务

    请求体:
        scrape_depth: int - 抓取深度 (50/100/200)，可覆盖项目默认值
    """
    project = _projects.get(project_id)
    if not project or project["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    if project["status"] in ("scraping", "analyzing"):
        return jsonify({"success": False, "error": "项目正在处理中，请稍后再试"}), 409

    data = request.get_json() or {}
    scrape_depth = data.get("scrape_depth", project["scrape_depth"])

    # 创建抓取任务
    task_id = str(uuid.uuid4())[:12]
    _scrape_tasks[task_id] = {
        "task_id": task_id,
        "project_id": project_id,
        "status": "queued",
        "scrape_depth": scrape_depth,
        "created_at": datetime.now().isoformat(),
    }

    # 更新项目状态
    project["status"] = "scraping"
    project["updated_at"] = datetime.now().isoformat()

    # 在生产环境中，这里应该将任务推入 Celery 队列
    # 当前为同步模拟：直接执行抓取逻辑
    _execute_scrape(project, scrape_depth, task_id)

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": "queued",
        },
    })


def _execute_scrape(project: dict, scrape_depth: int, task_id: str):
    """
    执行数据抓取（同步模拟，生产环境应为 Celery 异步任务）

    双重匹配降级逻辑（PRD 3.1.2）:
    1. 首选匹配：ASIN -> SP-API
    2. 降级匹配：Search Term -> SP-API keywords
    3. 多结果处理：取 BSR 最高的第一个产品
    """
    try:
        keyword = project.get("keyword", "")
        marketplace = project.get("marketplace_id", "ATVPDKIKX0DER")

        products = []

        # 尝试使用 Amazon SP-API
        try:
            from scrapers.amazon.sp_api_client import AmazonSPAPIClient
            from auth.api_keys_config import APIKeysConfigManager

            user_id = project["user_id"]
            config = APIKeysConfigManager.get_service_config(user_id, "amazon_sp_api", decrypt=True)

            if config and config.get("credentials"):
                sp_client = AmazonSPAPIClient(
                    credentials=config["credentials"],
                    marketplace=_marketplace_code(marketplace),
                )
                raw_products = sp_client.search_catalog(keyword, max_results=scrape_depth)
                products = raw_products
        except Exception as e:
            logger.warning(f"SP-API 抓取失败，降级到爬虫: {e}")

        # 降级到 Amazon 搜索爬虫
        if not products:
            try:
                from scrapers.amazon.search_crawler import AmazonSearchCrawler
                crawler = AmazonSearchCrawler(marketplace=_marketplace_code(marketplace))
                products = crawler.search(keyword, max_products=scrape_depth)
                crawler.close()
            except Exception as e:
                logger.warning(f"Amazon 爬虫抓取失败: {e}")

        # 存储产品数据
        _project_products[project["project_id"]] = products

        # 更新项目状态
        project["status"] = "scraped"
        project["product_count"] = len(products)
        project["updated_at"] = datetime.now().isoformat()

        _scrape_tasks[task_id]["status"] = "completed"

    except Exception as e:
        project["status"] = "failed"
        project["error_message"] = str(e)
        _scrape_tasks[task_id]["status"] = "failed"
        logger.error(f"抓取任务失败: {e}")


def _marketplace_code(marketplace_id: str) -> str:
    """将 Marketplace ID 转换为国家代码"""
    mapping = {
        "ATVPDKIKX0DER": "US",
        "A1F83G8C2ARO7P": "UK",
        "A1PA6795UKMFR9": "DE",
        "A1VC38T7YXB528": "JP",
        "A2EUQ1WTGCTBG2": "CA",
    }
    return mapping.get(marketplace_id, "US")


# ============================================================
# 产品列表与筛选
# ============================================================

@project_bp.route("/<project_id>/products", methods=["GET"])
@login_required
def get_products(current_user, project_id):
    """
    获取抓取结果列表

    查询参数:
        page: int - 页码
        page_size: int - 每页数量
        sort_by: str - 排序字段 (price, rating, review_count, est_sales_30d)
        sort_order: str - 排序方向 (asc/desc)
        min_price: float - 最低价格
        max_price: float - 最高价格
        min_reviews: int - 最少评论数
        min_rating: float - 最低评分
        exclude_brands: str - 排除品牌 (逗号分隔)
    """
    project = _projects.get(project_id)
    if not project or project["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    products = _project_products.get(project_id, [])

    # 应用筛选条件
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_reviews = request.args.get("min_reviews", type=int)
    min_rating = request.args.get("min_rating", type=float)
    exclude_brands = request.args.get("exclude_brands", "")

    filtered = []
    for p in products:
        if p.get("is_filtered"):
            continue
        price = p.get("price") or p.get("price_current") or 0
        if min_price and price < min_price:
            continue
        if max_price and price > max_price:
            continue
        if min_reviews and (p.get("review_count", 0) or 0) < min_reviews:
            continue
        if min_rating and (p.get("rating", 0) or 0) < min_rating:
            continue
        if exclude_brands:
            brands = [b.strip().lower() for b in exclude_brands.split(",")]
            if (p.get("brand", "") or "").lower() in brands:
                continue
        filtered.append(p)

    # 排序
    sort_by = request.args.get("sort_by", "")
    sort_order = request.args.get("sort_order", "desc")
    if sort_by and sort_by in ("price", "rating", "review_count", "est_sales_30d"):
        filtered.sort(
            key=lambda x: x.get(sort_by) or 0,
            reverse=(sort_order == "desc"),
        )

    # 分页
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 50, type=int)
    total_count = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "success": True,
        "data": {
            "products": filtered[start:end],
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        },
    })


@project_bp.route("/<project_id>/filter/ai", methods=["POST"])
@login_required
@quota_required("analysis")
def ai_filter(current_user, project_id):
    """
    AI 智能过滤

    请求体:
        user_description: str - 用户描述的产品特征
            例如: "带手柄的保温杯，排除杯盖等配件"
    """
    project = _projects.get(project_id)
    if not project or project["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    data = request.get_json() or {}
    user_description = data.get("user_description", "").strip()
    if not user_description:
        return jsonify({"success": False, "error": "请描述您想要保留的产品特征"}), 400

    products = _project_products.get(project_id, [])
    if not products:
        return jsonify({"success": False, "error": "项目中没有产品数据"}), 400

    # 调用 AI 过滤
    try:
        from analysis.amazon_data_filter import AmazonDataFilter
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(current_user["user_id"])
        data_filter = AmazonDataFilter()
        filtered = data_filter.ai_filter(products, user_description, ai_client=ai_client)

        # 提取保留的 ASIN 列表
        kept_asins = [
            p.get("asin") or p.get("coupang_product_id", "")
            for p in filtered
            if not p.get("is_filtered")
        ]

        # 更新项目
        project["filtered_count"] = len(kept_asins)
        project["status"] = "filtering"
        project["updated_at"] = datetime.now().isoformat()

        return jsonify({
            "success": True,
            "data": {
                "filtered_asin_list": kept_asins,
                "total_before": len(products),
                "total_after": len(kept_asins),
            },
        })

    except Exception as e:
        logger.error(f"AI 过滤失败: {e}")
        return jsonify({"success": False, "error": f"AI 过滤失败: {str(e)}"}), 500
