"""
数据抓取异步任务
对应 PRD 7 - 异步任务队列 (抓取相关)

任务:
    - scrape_project: 执行选品项目的数据抓取
    - scrape_product_details: 批量抓取产品详情页
    - cleanup_expired_tasks: 清理过期任务
"""

import os
import sys
from datetime import datetime

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery
from utils.logger import get_logger

logger = get_logger()


@celery.task(bind=True, name="tasks.scraping_tasks.scrape_project", max_retries=2)
def scrape_project(self, project_id: str, user_id: int, keyword: str,
                   marketplace: str = "US", scrape_depth: int = 100):
    """
    执行选品项目的数据抓取

    :param project_id: 项目 ID
    :param user_id: 用户 ID
    :param keyword: 搜索关键词
    :param marketplace: 站点代码
    :param scrape_depth: 抓取深度
    """
    logger.info(f"[Task] 开始抓取项目 {project_id}: keyword={keyword}, depth={scrape_depth}")

    try:
        # 更新任务状态
        self.update_state(state="PROGRESS", meta={
            "project_id": project_id,
            "step": "searching",
            "progress": 10,
        })

        products = []

        # 尝试 SP-API
        try:
            from scrapers.amazon.sp_api_client import AmazonSPAPIClient
            from auth.api_keys_config import APIKeysConfigManager

            config = APIKeysConfigManager.get_service_config(user_id, "amazon_sp_api", decrypt=True)
            if config and config.get("credentials"):
                sp_client = AmazonSPAPIClient(
                    credentials=config["credentials"],
                    marketplace=marketplace,
                )
                products = sp_client.search_catalog(keyword, max_results=scrape_depth)
                logger.info(f"SP-API 返回 {len(products)} 个产品")
        except Exception as e:
            logger.warning(f"SP-API 失败，降级到爬虫: {e}")

        # 降级到爬虫
        if not products:
            try:
                from scrapers.amazon.search_crawler import AmazonSearchCrawler
                crawler = AmazonSearchCrawler(marketplace=marketplace)
                products = crawler.search(keyword, max_products=scrape_depth)
                crawler.close()
            except Exception as e:
                logger.warning(f"Amazon 爬虫失败: {e}")

        self.update_state(state="PROGRESS", meta={
            "project_id": project_id,
            "step": "completed",
            "progress": 100,
            "product_count": len(products),
        })

        # 持久化到数据库
        try:
            _save_products_to_db(project_id, products)
        except Exception as e:
            logger.warning(f"产品数据入库失败: {e}")

        return {
            "project_id": project_id,
            "product_count": len(products),
            "status": "completed",
        }

    except Exception as exc:
        logger.error(f"抓取任务失败: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery.task(bind=True, name="tasks.scraping_tasks.scrape_product_details",
             max_retries=2, rate_limit="5/m")
def scrape_product_details(self, asins: list, marketplace: str = "US",
                           user_id: int = None):
    """
    批量抓取产品详情页

    :param asins: ASIN 列表
    :param marketplace: 站点代码
    :param user_id: 用户 ID
    """
    logger.info(f"[Task] 批量抓取详情页: {len(asins)} 个 ASIN")

    results = []
    total = len(asins)

    try:
        from scrapers.amazon.detail_crawler import AmazonDetailCrawler
        from utils.http_client import HttpClient

        http_client = HttpClient(min_delay=2.0, max_delay=4.0)
        crawler = AmazonDetailCrawler(http_client=http_client, marketplace=marketplace)

        try:
            for i, asin in enumerate(asins):
                self.update_state(state="PROGRESS", meta={
                    "current": i + 1,
                    "total": total,
                    "progress": int((i + 1) / total * 100),
                })

                detail = crawler.crawl_detail(asin)
                if detail:
                    results.append(detail)
        finally:
            crawler.close()
            http_client.close()

        return {
            "total_requested": total,
            "total_crawled": len(results),
            "results": results,
        }

    except Exception as exc:
        logger.error(f"详情页抓取失败: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery.task(name="tasks.scraping_tasks.cleanup_expired_tasks")
def cleanup_expired_tasks():
    """清理过期任务数据（定时任务，每小时执行）"""
    logger.info("[Task] 清理过期任务数据")

    try:
        from database.connection import DatabaseManager
        db = DatabaseManager()

        # 清理 7 天前的已完成任务
        db.execute("""
            DELETE FROM analysis_tasks
            WHERE status IN ('completed', 'failed')
            AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)

        logger.info("过期任务清理完成")

    except Exception as e:
        logger.error(f"清理过期任务失败: {e}")


def _save_products_to_db(project_id: str, products: list):
    """将产品数据保存到数据库

    兼容多种爬虫输出的字段名:
    - 图片: main_image / main_image_url / image_url
    - 价格: price / price_current
    - BSR: bsr / bsr_rank
    - 物流: fulfillment_type / fulfillment
    - 月销量: estimated_monthly_sales / est_sales_30d / monthly_sales
    """
    try:
        from database.connection import DatabaseManager
        import json

        db = DatabaseManager()

        for product in products:
            # 兼容不同爬虫的字段名
            image_url = (
                product.get("main_image_url")
                or product.get("main_image")
                or product.get("image_url")
                or ""
            )
            price = product.get("price_current") or product.get("price")
            bsr_rank = product.get("bsr_rank") or product.get("bsr") or 0
            fulfillment = product.get("fulfillment_type") or product.get("fulfillment") or ""
            est_sales = (
                product.get("est_sales_30d")
                or product.get("estimated_monthly_sales")
                or product.get("monthly_sales")
                or 0
            )
            bsr_category = (
                product.get("bsr_category")
                or product.get("category")
                or ""
            )

            db.execute("""
                INSERT INTO project_products
                (project_id, asin, title, brand, main_image_url, price_current,
                 rating, review_count, bsr_rank, bsr_category,
                 fulfillment_type, est_sales_30d, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project_id,
                product.get("asin", ""),
                product.get("title", ""),
                product.get("brand", ""),
                image_url,
                price,
                product.get("rating"),
                product.get("review_count", 0),
                bsr_rank,
                bsr_category,
                fulfillment,
                int(est_sales) if est_sales else None,
                json.dumps(product, ensure_ascii=False, default=str),
            ))

        # 更新项目产品数量
        db.execute("""
            UPDATE sourcing_projects SET product_count = %s, status = 'scraped'
            WHERE id = %s
        """, (len(products), project_id))

    except Exception as e:
        logger.error(f"产品数据入库失败: {e}")
        raise
