"""
维护异步任务
定时数据清理、归档等运维任务
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery
from utils.logger import get_logger

logger = get_logger()


@celery.task(bind=True, name="tasks.maintenance_tasks.run_data_cleanup",
             max_retries=1, time_limit=300)
def run_data_cleanup(self):
    """
    定时数据清理任务 (每天执行一次)
    清理过期任务结果、审计日志、通知、临时文件等
    """
    logger.info("[Maintenance] 开始定时数据清理")
    try:
        from utils.data_cleaner import cleaner
        result = cleaner.run_all(dry_run=False)
        logger.info(f"[Maintenance] 清理完成: {result.get('total_cleaned', 0)} 条记录")
        return result
    except Exception as e:
        logger.error(f"[Maintenance] 数据清理失败: {e}")
        raise self.retry(exc=e, countdown=300)
