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

import json
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

project_bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


# ============================================================
# 数据库辅助函数
# ============================================================

def _get_db():
    """获取数据库连接（优雅降级到内存模式）"""
    try:
        from database.connection import db
        # 测试连接是否可用
        db.fetch_one("SELECT 1")
        return db
    except Exception:
        return None


# 内存降级存储（数据库不可用时使用）
_mem_projects = {}
_mem_products = {}
_mem_scrape_tasks = {}


def _db_create_project(db, project_data: dict) -> int:
    """在数据库中创建项目，返回项目ID"""
    return db.insert_and_get_id("""
        INSERT INTO sourcing_projects
        (user_id, name, marketplace_id, keyword, file_upload_id, scrape_depth, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        project_data["user_id"],
        project_data["name"],
        project_data["marketplace_id"],
        project_data.get("keyword"),
        project_data.get("file_upload_id"),
        project_data.get("scrape_depth", 100),
        "created",
    ))


def _db_get_project(db, project_id, user_id: int) -> dict | None:
    """从数据库获取项目"""
    row = db.fetch_one("""
        SELECT id AS project_id, user_id, name, marketplace_id, keyword,
               file_upload_id, scrape_depth, status, product_count,
               filtered_count, error_message, created_at, updated_at
        FROM sourcing_projects
        WHERE id = %s AND user_id = %s
    """, (project_id, user_id))
    if row:
        row["project_id"] = str(row["project_id"])
        row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
        row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
    return row


def _db_list_projects(db, user_id: int, page: int, page_size: int) -> tuple:
    """从数据库获取项目列表，返回 (projects, total_count)"""
    total = db.fetch_one(
        "SELECT COUNT(*) AS cnt FROM sourcing_projects WHERE user_id = %s",
        (user_id,)
    )
    total_count = total["cnt"] if total else 0

    offset = (page - 1) * page_size
    rows = db.fetch_all("""
        SELECT id AS project_id, user_id, name, marketplace_id, keyword,
               scrape_depth, status, product_count, filtered_count,
               created_at, updated_at
        FROM sourcing_projects
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, page_size, offset))

    for row in rows:
        row["project_id"] = str(row["project_id"])
        row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
        row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None

    return rows, total_count


def _db_delete_project(db, project_id, user_id: int) -> bool:
    """从数据库删除项目"""
    affected = db.execute(
        "DELETE FROM sourcing_projects WHERE id = %s AND user_id = %s",
        (project_id, user_id)
    )
    return affected > 0


def _db_update_project_status(db, project_id, status: str, **kwargs):
    """更新项目状态"""
    sets = ["status = %s"]
    params = [status]
    for key, val in kwargs.items():
        sets.append(f"{key} = %s")
        params.append(val)
    params.append(project_id)
    db.execute(
        f"UPDATE sourcing_projects SET {', '.join(sets)} WHERE id = %s",
        tuple(params)
    )


def _db_get_products(db, project_id, filters: dict, page: int, page_size: int) -> tuple:
    """从数据库获取产品列表"""
    where_clauses = ["project_id = %s"]
    params = [project_id]

    if not filters.get("include_filtered"):
        where_clauses.append("is_filtered = 0")

    if filters.get("min_price"):
        where_clauses.append("price_current >= %s")
        params.append(filters["min_price"])
    if filters.get("max_price"):
        where_clauses.append("price_current <= %s")
        params.append(filters["max_price"])
    if filters.get("min_reviews"):
        where_clauses.append("review_count >= %s")
        params.append(filters["min_reviews"])
    if filters.get("min_rating"):
        where_clauses.append("rating >= %s")
        params.append(filters["min_rating"])
    if filters.get("exclude_brands"):
        brands = [b.strip() for b in filters["exclude_brands"].split(",") if b.strip()]
        if brands:
            placeholders = ", ".join(["%s"] * len(brands))
            where_clauses.append(f"(brand IS NULL OR brand NOT IN ({placeholders}))")
            params.extend(brands)

    where_sql = " AND ".join(where_clauses)

    # 排序
    sort_by = filters.get("sort_by", "created_at")
    allowed_sorts = {"price_current", "rating", "review_count", "est_sales_30d", "bsr_rank", "created_at"}
    if sort_by not in allowed_sorts:
        sort_by = "created_at"
    sort_order = "ASC" if filters.get("sort_order") == "asc" else "DESC"

    # 总数
    total = db.fetch_one(
        f"SELECT COUNT(*) AS cnt FROM project_products WHERE {where_sql}",
        tuple(params)
    )
    total_count = total["cnt"] if total else 0

    # 分页查询
    offset = (page - 1) * page_size
    rows = db.fetch_all(f"""
        SELECT id, project_id, asin, marketplace_id, title, brand,
               main_image_url, price_current, fulfillment_type, rating,
               review_count, est_sales_30d, cvr_30d, bsr_rank, bsr_category,
               is_filtered, filter_reason, created_at
        FROM project_products
        WHERE {where_sql}
        ORDER BY {sort_by} {sort_order}
        LIMIT %s OFFSET %s
    """, tuple(params) + (page_size, offset))

    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()
        # 兼容前端字段名（前端使用 price/bsr/monthly_sales/main_image/fulfillment）
        row["price"] = float(row["price_current"]) if row.get("price_current") else None
        row["bsr"] = row.get("bsr_rank")
        row["monthly_sales"] = row.get("est_sales_30d")
        row["main_image"] = row.get("main_image_url")
        row["image_url"] = row.get("main_image_url")
        row["fulfillment"] = row.get("fulfillment_type")

    return rows, total_count


# ============================================================
# 项目管理
# ============================================================

@project_bp.route("/create", methods=["POST"])
@login_required
def create_project(current_user):
    """创建选品项目"""
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "项目名称不能为空"}), 400

    keyword = data.get("keyword", "").strip()
    file_upload_id = data.get("file_upload_id", "").strip()
    if not keyword and not file_upload_id:
        return jsonify({"success": False, "error": "请提供搜索关键词或上传数据文件"}), 400

    user_id = current_user["user_id"]
    project_data = {
        "user_id": user_id,
        "name": name,
        "marketplace_id": data.get("marketplace_id", "ATVPDKIKX0DER"),
        "keyword": keyword,
        "file_upload_id": file_upload_id,
        "scrape_depth": data.get("scrape_depth", 100),
    }

    db = _get_db()
    if db:
        project_id = _db_create_project(db, project_data)
        project_id_str = str(project_id)
    else:
        # 内存降级
        import uuid
        project_id_str = str(uuid.uuid4())[:8]
        _mem_projects[project_id_str] = {
            **project_data,
            "project_id": project_id_str,
            "status": "created",
            "product_count": 0,
            "filtered_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    logger.info(f"用户 {user_id} 创建选品项目: {name} ({project_id_str})")

    return jsonify({
        "success": True,
        "data": {"project_id": project_id_str},
    }), 201


@project_bp.route("", methods=["GET"])
@login_required
def list_projects(current_user):
    """获取用户的项目列表"""
    user_id = current_user["user_id"]
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    db = _get_db()
    if db:
        projects, total_count = _db_list_projects(db, user_id, page, page_size)
    else:
        user_projects = sorted(
            [p for p in _mem_projects.values() if p["user_id"] == user_id],
            key=lambda x: x["created_at"],
            reverse=True,
        )
        total_count = len(user_projects)
        start = (page - 1) * page_size
        projects = user_projects[start:start + page_size]

    return jsonify({
        "success": True,
        "data": {
            "projects": projects,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        },
    })


@project_bp.route("/<project_id>", methods=["GET"])
@login_required
def get_project(current_user, project_id):
    """获取项目详情"""
    db = _get_db()
    if db:
        project = _db_get_project(db, project_id, current_user["user_id"])
    else:
        project = _mem_projects.get(project_id)
        if project and project["user_id"] != current_user["user_id"]:
            project = None

    if not project:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    return jsonify({"success": True, "data": project})


@project_bp.route("/<project_id>", methods=["DELETE"])
@login_required
def delete_project(current_user, project_id):
    """删除项目"""
    db = _get_db()
    if db:
        deleted = _db_delete_project(db, project_id, current_user["user_id"])
        if not deleted:
            return jsonify({"success": False, "error": "项目不存在"}), 404
    else:
        project = _mem_projects.get(project_id)
        if not project or project["user_id"] != current_user["user_id"]:
            return jsonify({"success": False, "error": "项目不存在"}), 404
        del _mem_projects[project_id]
        _mem_products.pop(project_id, None)

    return jsonify({"success": True, "message": "项目已删除"})


# ============================================================
# 数据抓取
# ============================================================

@project_bp.route("/<project_id>/scrape", methods=["POST"])
@login_required
@quota_required("scrape")
def scrape_project(current_user, project_id):
    """发起数据抓取任务"""
    user_id = current_user["user_id"]

    db = _get_db()
    if db:
        project = _db_get_project(db, project_id, user_id)
    else:
        project = _mem_projects.get(project_id)
        if project and project["user_id"] != user_id:
            project = None

    if not project:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    if project["status"] in ("scraping", "analyzing"):
        return jsonify({"success": False, "error": "项目正在处理中，请稍后再试"}), 409

    data = request.get_json() or {}
    scrape_depth = data.get("scrape_depth", project.get("scrape_depth", 100))

    # 更新项目状态为 scraping
    if db:
        _db_update_project_status(db, project_id, "scraping")

    # 尝试通过 Celery 异步执行
    celery_dispatched = False
    try:
        from tasks.scraping_tasks import scrape_amazon_products
        task = scrape_amazon_products.delay(
            project_id=int(project_id) if project_id.isdigit() else project_id,
            keyword=project.get("keyword", ""),
            marketplace=_marketplace_code(project.get("marketplace_id", "ATVPDKIKX0DER")),
            scrape_depth=scrape_depth,
            user_id=user_id,
        )
        celery_dispatched = True
        task_id = task.id
        logger.info(f"抓取任务已推入 Celery 队列: {task_id}")
    except Exception as e:
        logger.warning(f"Celery 不可用，降级到同步执行: {e}")

    if not celery_dispatched:
        # 同步降级执行
        import uuid
        task_id = str(uuid.uuid4())[:12]
        _execute_scrape_sync(project, project_id, scrape_depth, task_id, db)

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": "queued",
            "async": celery_dispatched,
        },
    })


def _execute_scrape_sync(project: dict, project_id: str, scrape_depth: int,
                         task_id: str, db):
    """同步执行抓取（Celery 不可用时的降级方案）"""
    try:
        keyword = project.get("keyword", "")
        marketplace = _marketplace_code(project.get("marketplace_id", "ATVPDKIKX0DER"))
        products = []

        # 尝试 SP-API
        try:
            from scrapers.amazon.sp_api_client import AmazonSPAPIClient
            from auth.api_keys_config import APIKeysConfigManager
            user_id = project["user_id"]
            config = APIKeysConfigManager.get_service_config(user_id, "amazon_sp_api", decrypt=True)
            if config and config.get("credentials"):
                sp_client = AmazonSPAPIClient(
                    credentials=config["credentials"],
                    marketplace=marketplace,
                )
                products = sp_client.search_catalog(keyword, max_results=scrape_depth)
        except Exception as e:
            logger.warning(f"SP-API 抓取失败，降级到爬虫: {e}")

        # 降级到爬虫
        if not products:
            try:
                from scrapers.amazon.search_crawler import AmazonSearchCrawler
                crawler = AmazonSearchCrawler(marketplace=marketplace)
                products = crawler.search(keyword, max_products=scrape_depth)
                crawler.close()
            except Exception as e:
                logger.warning(f"Amazon 爬虫抓取失败: {e}")

        # 持久化
        if db:
            try:
                for p in products:
                    # 兼容爬虫(main_image)和SP-API(main_image)以及DB字段(main_image_url)
                    image_url = (
                        p.get("main_image_url")
                        or p.get("main_image")
                        or ""
                    )
                    # 兼容不同来源的价格字段
                    price = p.get("price_current") or p.get("price")
                    # BSR: 兼容 bsr_rank / bsr
                    bsr_rank = p.get("bsr_rank") or p.get("bsr") or 0
                    # 物流方式
                    fulfillment = (
                        p.get("fulfillment_type")
                        or p.get("fulfillment", {}).get("type", "")
                        if isinstance(p.get("fulfillment"), dict)
                        else p.get("fulfillment_type", "")
                    )

                    # 预估销量
                    est_sales = (
                        p.get("est_sales_30d")
                        or p.get("estimated_monthly_sales")
                        or p.get("monthly_sales")
                    )
                    # BSR 类目
                    bsr_category = (
                        p.get("bsr_category")
                        or p.get("category")
                        or ""
                    )
                    db.execute("""
                        INSERT INTO project_products
                        (project_id, asin, title, brand, main_image_url,
                         price_current, rating, review_count, bsr_rank,
                         bsr_category, est_sales_30d,
                         fulfillment_type, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        project_id,
                        p.get("asin", ""),
                        p.get("title", ""),
                        p.get("brand", ""),
                        image_url,
                        price,
                        p.get("rating"),
                        p.get("review_count", 0),
                        bsr_rank,
                        bsr_category,
                        int(est_sales) if est_sales else None,
                        fulfillment,
                        json.dumps(p, ensure_ascii=False, default=str),
                    ))
                _db_update_project_status(
                    db, project_id, "scraped",
                    product_count=len(products)
                )
            except Exception as e:
                logger.error(f"产品数据入库失败: {e}")
                _db_update_project_status(db, project_id, "failed", error_message=str(e))
        else:
            _mem_products[project_id] = products
            if project_id in _mem_projects:
                _mem_projects[project_id]["status"] = "scraped"
                _mem_projects[project_id]["product_count"] = len(products)

    except Exception as e:
        if db:
            _db_update_project_status(db, project_id, "failed", error_message=str(e))
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
    """获取抓取结果列表"""
    user_id = current_user["user_id"]

    # 验证项目归属
    db = _get_db()
    if db:
        project = _db_get_project(db, project_id, user_id)
    else:
        project = _mem_projects.get(project_id)
        if project and project["user_id"] != user_id:
            project = None

    if not project:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 50, type=int)

    if db:
        filters = {
            "min_price": request.args.get("min_price", type=float),
            "max_price": request.args.get("max_price", type=float),
            "min_reviews": request.args.get("min_reviews", type=int),
            "min_rating": request.args.get("min_rating", type=float),
            "exclude_brands": request.args.get("exclude_brands", ""),
            "sort_by": request.args.get("sort_by", "created_at"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        products, total_count = _db_get_products(db, project_id, filters, page, page_size)
    else:
        # 内存降级
        products = _mem_products.get(project_id, [])
        products = _apply_mem_filters(products, request.args)
        total_count = len(products)
        start = (page - 1) * page_size
        products = products[start:start + page_size]

    return jsonify({
        "success": True,
        "data": {
            "products": products,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        },
    })


def _apply_mem_filters(products: list, args) -> list:
    """内存模式下的产品筛选"""
    min_price = args.get("min_price", type=float)
    max_price = args.get("max_price", type=float)
    min_reviews = args.get("min_reviews", type=int)
    min_rating = args.get("min_rating", type=float)
    exclude_brands = args.get("exclude_brands", "")

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

    sort_by = args.get("sort_by", "")
    sort_order = args.get("sort_order", "desc")
    if sort_by and sort_by in ("price", "rating", "review_count", "est_sales_30d"):
        filtered.sort(key=lambda x: x.get(sort_by) or 0, reverse=(sort_order == "desc"))

    return filtered


@project_bp.route("/<project_id>/filter/rules", methods=["POST"])
@login_required
def rule_filter(current_user, project_id):
    """规则过滤：根据用户设定的规则过滤产品"""
    user_id = current_user["user_id"]

    db = _get_db()
    if db:
        project = _db_get_project(db, project_id, user_id)
    else:
        project = _mem_projects.get(project_id)
        if project and project["user_id"] != user_id:
            project = None

    if not project:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    data = request.get_json() or {}
    rules = data.get("rules", {})
    if not rules:
        return jsonify({"success": False, "error": "请提供过滤规则"}), 400

    min_price = rules.get("min_price")
    max_price = rules.get("max_price")
    min_reviews = rules.get("min_reviews")
    max_reviews = rules.get("max_reviews")
    min_rating = rules.get("min_rating")
    min_monthly_sales = rules.get("min_monthly_sales")
    exclude_brands = rules.get("exclude_brands", [])

    if db:
        # 获取未过滤的产品
        rows = db.fetch_all(
            "SELECT * FROM project_products WHERE project_id = %s AND is_filtered = 0",
            (project_id,)
        )
        filtered_asins = []
        for p in rows:
            price = p.get("price_current") or p.get("price") or 0
            reviews = p.get("review_count") or 0
            rating = p.get("rating") or 0
            sales = p.get("est_sales_30d") or 0
            brand = (p.get("brand") or "").lower()

            should_filter = False
            if min_price and price < min_price:
                should_filter = True
            if max_price and price > max_price:
                should_filter = True
            if min_reviews and reviews < min_reviews:
                should_filter = True
            if max_reviews and reviews > max_reviews:
                should_filter = True
            if min_rating and rating < min_rating:
                should_filter = True
            if min_monthly_sales and sales < min_monthly_sales:
                should_filter = True
            if exclude_brands and brand in [b.lower() for b in exclude_brands]:
                should_filter = True

            if should_filter:
                filtered_asins.append(p.get("asin"))

        if filtered_asins:
            placeholders = ", ".join(["%s"] * len(filtered_asins))
            db.execute(f"""
                UPDATE project_products
                SET is_filtered = 1, filter_reason = 'rule_filter'
                WHERE project_id = %s AND asin IN ({placeholders})
            """, (project_id, *filtered_asins))

        total_before = len(rows)
        total_after = total_before - len(filtered_asins)

        _db_update_project_status(
            db, project_id, "filtered",
            filtered_count=total_after
        )
    else:
        # 内存降级
        products = _mem_products.get(project_id, [])
        filtered_count = 0
        for p in products:
            if p.get("is_filtered"):
                continue
            price = p.get("price") or p.get("price_current") or 0
            reviews = p.get("review_count") or 0
            rating = p.get("rating") or 0
            sales = p.get("est_sales_30d") or 0
            brand = (p.get("brand") or "").lower()

            should_filter = False
            if min_price and price < min_price:
                should_filter = True
            if max_price and price > max_price:
                should_filter = True
            if min_reviews and reviews < min_reviews:
                should_filter = True
            if max_reviews and reviews > max_reviews:
                should_filter = True
            if min_rating and rating < min_rating:
                should_filter = True
            if min_monthly_sales and sales < min_monthly_sales:
                should_filter = True
            if exclude_brands and brand in [b.lower() for b in exclude_brands]:
                should_filter = True

            if should_filter:
                p["is_filtered"] = True
                p["filter_reason"] = "rule_filter"
                filtered_count += 1

        total_before = len([p for p in products])
        total_after = len([p for p in products if not p.get("is_filtered")])

    logger.info(f"用户 {user_id} 规则过滤项目 {project_id}: {total_before} -> {total_after}")

    return jsonify({
        "success": True,
        "data": {
            "total_before": total_before,
            "total_after": total_after,
            "rules_applied": rules,
        },
    })


@project_bp.route("/<project_id>/filter/ai", methods=["POST"])
@login_required
@quota_required("analysis")
def ai_filter(current_user, project_id):
    """AI 智能过滤"""
    user_id = current_user["user_id"]

    db = _get_db()
    if db:
        project = _db_get_project(db, project_id, user_id)
    else:
        project = _mem_projects.get(project_id)
        if project and project["user_id"] != user_id:
            project = None

    if not project:
        return jsonify({"success": False, "error": "项目不存在"}), 404

    data = request.get_json() or {}
    user_description = data.get("user_description", "").strip()
    if not user_description:
        return jsonify({"success": False, "error": "请描述您想要保留的产品特征"}), 400

    # 获取产品数据
    if db:
        rows = db.fetch_all(
            "SELECT * FROM project_products WHERE project_id = %s AND is_filtered = 0",
            (project_id,)
        )
        products = rows
    else:
        products = [p for p in _mem_products.get(project_id, []) if not p.get("is_filtered")]

    if not products:
        return jsonify({"success": False, "error": "项目中没有产品数据"}), 400

    try:
        from analysis.amazon_data_filter import AmazonDataFilter
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        data_filter = AmazonDataFilter()
        filtered = data_filter.ai_filter(products, user_description, ai_client=ai_client)

        kept_asins = [
            p.get("asin") or p.get("coupang_product_id", "")
            for p in filtered
            if not p.get("is_filtered")
        ]

        # 更新数据库中被过滤的产品
        if db:
            filtered_asins = [
                p.get("asin") for p in filtered if p.get("is_filtered")
            ]
            if filtered_asins:
                placeholders = ", ".join(["%s"] * len(filtered_asins))
                db.execute(f"""
                    UPDATE project_products
                    SET is_filtered = 1, filter_reason = 'AI filter'
                    WHERE project_id = %s AND asin IN ({placeholders})
                """, (project_id, *filtered_asins))

            _db_update_project_status(
                db, project_id, "filtering",
                filtered_count=len(kept_asins)
            )

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
