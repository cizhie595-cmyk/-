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
            reviews = review_crawler.crawl_reviews(asin, max_reviews=max_reviews)
        finally:
            review_crawler.close()

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

        ai_client = AIConfigManager.create_client(user_id)
        generator = ReportGenerator(ai_client=ai_client)

        self.update_state(state="PROGRESS", meta={
            "task_id": task_id,
            "step": "generating_report",
            "progress": 50,
        })

        report_path = generator.generate(
            keyword=project_id or "analysis",
            products=[],
            category_analysis={},
            profit_results=[],
            review_analyses={},
            detail_analyses={},
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
