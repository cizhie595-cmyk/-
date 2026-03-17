"""
Celery 应用配置
对应 PRD 7 - 异步任务队列

使用方式:
    # 启动 Worker
    celery -A celery_app.celery worker --loglevel=info --concurrency=4

    # 启动 Beat (定时任务)
    celery -A celery_app.celery beat --loglevel=info

    # 监控 (Flower)
    celery -A celery_app.celery flower --port=5555
"""

import os

from celery import Celery

# Redis 连接配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", "redis://localhost:6379/1")


def make_celery(app_name: str = "coupang_selection") -> Celery:
    """
    创建 Celery 实例

    :param app_name: 应用名称
    :return: Celery 实例
    """
    celery = Celery(
        app_name,
        broker=REDIS_URL,
        backend=REDIS_RESULT_URL,
    )

    celery.conf.update(
        # 序列化
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",

        # 时区
        timezone="Asia/Shanghai",
        enable_utc=True,

        # 任务配置
        task_track_started=True,
        task_time_limit=3600,           # 单任务最大执行时间: 1小时
        task_soft_time_limit=3000,      # 软超时: 50分钟
        task_acks_late=True,            # 任务完成后才确认
        worker_prefetch_multiplier=1,   # 每个 Worker 预取 1 个任务

        # 结果配置
        result_expires=86400,           # 结果保留 24 小时

        # 重试配置
        task_default_retry_delay=60,    # 默认重试间隔 60 秒
        task_max_retries=3,             # 最大重试次数

        # 路由配置
        task_routes={
            "tasks.scraping_tasks.*": {"queue": "scraping"},
            "tasks.analysis_tasks.*": {"queue": "analysis"},
            "tasks.threed_tasks.*": {"queue": "threed"},
        },

        # 定时任务 (Beat)
        beat_schedule={
            "cleanup-expired-tasks": {
                "task": "tasks.scraping_tasks.cleanup_expired_tasks",
                "schedule": 3600.0,  # 每小时执行一次
            },
        },
    )

    # 自动发现任务模块
    celery.autodiscover_tasks(["tasks"])

    return celery


# 全局 Celery 实例
celery = make_celery()
