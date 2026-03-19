"""
分析异步任务
对应 PRD 7 - 异步任务队列 (分析相关)

任务:
    - run_visual_analysis: 执行视觉语义分析
    - run_review_analysis: 执行评论深度挖掘
    - generate_decision_report: 生成综合决策报告
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery
from utils.logger import get_logger

logger = get_logger()


@celery.task(bind=True, name="tasks.analysis_tasks.run_visual_analysis",
             max_retries=2, time_limit=600)
def run_visual_analysis(self, task_id: str, asin: str, user_id: int,
                        dimensions: list = None):
    """
    执行视觉语义分析

    :param task_id: 分析任务 ID
    :param asin: 目标 ASIN
    :param user_id: 用户 ID
    :param dimensions: 分析维度列表
    """
    logger.info(f"[Task] 视觉分析: ASIN={asin}, task_id={task_id}")

    try:
        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "crawling_detail",
            "progress": 20,
        })

        from scrapers.amazon.deep_crawler import AmazonDeepCrawler
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)
        crawler = AmazonDeepCrawler(ai_client=ai_client)

        try:
            self.update_state(state="PROGRESS", meta={
                "task_id": task_id,
                "step": "analyzing",
                "progress": 50,
            })

            result = crawler.deep_analyze(asin)
        finally:
            crawler.close()

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "saving",
            "progress": 90,
        })

        # 保存结果到数据库
        _save_analysis_result(task_id, "visual", result)

        return {
            "task_id": task_id,
            "asin": asin,
            "status": "completed",
            "result": result,
        }

    except Exception as exc:
        logger.error(f"视觉分析失败: {exc}")
        _update_task_status(task_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=120)


@celery.task(bind=True, name="tasks.analysis_tasks.run_review_analysis",
             max_retries=2, time_limit=900)
def run_review_analysis(self, task_id: str, asin: str, user_id: int,
                        max_reviews: int = 500):
    """
    执行评论深度挖掘

    :param task_id: 分析任务 ID
    :param asin: 目标 ASIN
    :param user_id: 用户 ID
    :param max_reviews: 最大评论数
    """
    logger.info(f"[Task] 评论分析: ASIN={asin}, max_reviews={max_reviews}")

    try:
        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "crawling_reviews",
            "progress": 20,
        })

        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
        from auth.ai_config import AIConfigManager

        ai_client = AIConfigManager.create_client(user_id)

        # 爬取评论
        review_crawler = AmazonReviewCrawler()
        try:
            crawl_result = review_crawler.crawl_reviews(asin, max_reviews=max_reviews)
        finally:
            review_crawler.close()

        # crawl_reviews 返回 dict，需要提取 reviews 列表
        if isinstance(crawl_result, dict):
            reviews = crawl_result.get("reviews", [])
        else:
            reviews = crawl_result or []

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "ai_analyzing",
            "progress": 60,
            "review_count": len(reviews),
        })

        # AI 分析
        analyzer = ReviewAnalyzer(ai_client=ai_client)
        analysis = analyzer.analyze(reviews, asin)

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "saving",
            "progress": 90,
        })

        # 保存结果
        _save_analysis_result(task_id, "reviews", analysis)

        return {
            "task_id": task_id,
            "asin": asin,
            "status": "completed",
            "review_count": len(reviews),
            "result": analysis,
        }

    except Exception as exc:
        logger.error(f"评论分析失败: {exc}")
        _update_task_status(task_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=120)


@celery.task(bind=True, name="tasks.analysis_tasks.generate_decision_report",
             max_retries=1, time_limit=600)
def generate_decision_report(self, task_id: str, user_id: int,
                             project_id: str = None, asin_list: list = None):
    """
    生成综合决策报告

    :param task_id: 任务 ID
    :param user_id: 用户 ID
    :param project_id: 项目 ID
    :param asin_list: ASIN 列表
    """
    logger.info(f"[Task] 生成决策报告: task_id={task_id}")

    try:
        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "collecting_data",
            "progress": 20,
        })

        from analysis.market_analysis.report_generator import ReportGenerator
        from auth.ai_config import AIConfigManager
        import json

        ai_client = AIConfigManager.create_client(user_id)
        generator = ReportGenerator(ai_client=ai_client)

        # ---- 收集项目数据 ----
        products = []
        keyword = project_id or "analysis"
        review_analyses = {}
        detail_analyses = {}
        profit_results = []
        category_analysis = {}

        try:
            from database.connection import DatabaseManager
            db = DatabaseManager()

            # 获取项目关键词
            if project_id:
                project_row = db.fetch_one(
                    "SELECT keyword FROM sourcing_projects WHERE id = %s AND user_id = %s",
                    (project_id, user_id),
                )
                if project_row and project_row.get("keyword"):
                    keyword = project_row["keyword"]

                # 获取产品数据
                product_rows = db.fetch_all("""
                    SELECT asin, title, brand, main_image_url, price_current,
                           fulfillment_type, rating, review_count, est_sales_30d,
                           bsr_rank, bsr_category
                    FROM project_products
                    WHERE project_id = %s AND is_filtered = 0
                    ORDER BY bsr_rank ASC LIMIT 200
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

            # 收集已完成的分析结果
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

            # 收集利润计算数据
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

            # 简单的类目分析（基于产品数据生成）
            if products:
                prices = [p["price"] for p in products if p.get("price")]
                ratings = [p["rating"] for p in products if p.get("rating")]
                reviews_list = [p["review_count"] for p in products if p.get("review_count")]
                sales = [p["estimated_monthly_sales"] for p in products if p.get("estimated_monthly_sales")]
                avg_price = sum(prices) / len(prices) if prices else 0
                total_sales = sum(sales)
                category_analysis = {
                    "market_size": {
                        "estimated_total_monthly_gmv": round(total_sales * avg_price, 2),
                        "estimated_monthly_sales": total_sales,
                        "product_count": len(products),
                        "avg_price": round(avg_price, 2),
                    },
                    "competition": {
                        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                        "avg_review_count": round(sum(reviews_list) / len(reviews_list)) if reviews_list else 0,
                        "avg_price": round(avg_price, 2),
                    },
                    "pricing": {
                        "min_price": round(min(prices), 2) if prices else 0,
                        "max_price": round(max(prices), 2) if prices else 0,
                        "avg_price": round(avg_price, 2),
                    },
                }

        except Exception as e:
            logger.warning(f"Celery 报告数据收集失败，使用空数据: {e}")

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "generating_report",
            "progress": 50,
            "product_count": len(products),
        })

        report_path = generator.generate(
            keyword=keyword,
            products=products,
            category_analysis=category_analysis,
            profit_results=profit_results,
            review_analyses=review_analyses,
            detail_analyses=detail_analyses,
            output_dir="reports",
        )

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "completed",
            "progress": 100,
        })

        _save_analysis_result(task_id, "report", {"report_url": report_path})

        return {
            "task_id": task_id,
            "status": "completed",
            "report_url": report_path,
        }

    except Exception as exc:
        logger.error(f"报告生成失败: {exc}")
        _update_task_status(task_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=60)


# ============================================================
# 辅助函数
# ============================================================

def _save_analysis_result(task_id: str, task_type: str, result: dict):
    """保存分析结果到数据库"""
    try:
        from database.connection import DatabaseManager
        import json

        db = DatabaseManager()
        db.execute("""
            UPDATE analysis_tasks
            SET status = 'completed',
                result_data = %s,
                completed_at = NOW()
            WHERE id = %s
        """, (json.dumps(result, ensure_ascii=False, default=str), task_id))

    except Exception as e:
        logger.warning(f"分析结果入库失败: {e}")


def _update_task_status(task_id: str, status: str, error_msg: str = None):
    """更新任务状态"""
    try:
        from database.connection import DatabaseManager

        db = DatabaseManager()
        db.execute("""
            UPDATE analysis_tasks
            SET status = %s, error_message = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, error_msg, task_id))

    except Exception as e:
        logger.warning(f"任务状态更新失败: {e}")
