"""
Coupang 选品系统 - Celery 异步任务状态实时推送
通过 WebSocket 和 SSE (Server-Sent Events) 将任务进度推送至前端
"""

import json
import time
import queue
import threading
from collections import defaultdict
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

# ============================================================
# SSE 事件管理器（支持无 WebSocket 场景）
# ============================================================

class SSEManager:
    """Server-Sent Events 管理器"""

    def __init__(self):
        self._subscribers = defaultdict(list)  # user_id -> [queue.Queue]
        self._lock = threading.Lock()

    def subscribe(self, user_id: int) -> queue.Queue:
        """用户订阅任务事件流"""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers[user_id].append(q)
        logger.debug(f"[SSE] User {user_id} subscribed (total: {len(self._subscribers[user_id])})")
        return q

    def unsubscribe(self, user_id: int, q: queue.Queue):
        """用户取消订阅"""
        with self._lock:
            if user_id in self._subscribers:
                try:
                    self._subscribers[user_id].remove(q)
                except ValueError:
                    pass
                if not self._subscribers[user_id]:
                    del self._subscribers[user_id]
        logger.debug(f"[SSE] User {user_id} unsubscribed")

    def publish(self, user_id: int, event: dict):
        """向用户推送事件"""
        with self._lock:
            queues = list(self._subscribers.get(user_id, []))

        dead_queues = []
        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead_queues.append(q)

        # 清理满队列
        if dead_queues:
            with self._lock:
                for q in dead_queues:
                    try:
                        self._subscribers[user_id].remove(q)
                    except (ValueError, KeyError):
                        pass

    def get_subscriber_count(self, user_id: int = None) -> int:
        """获取订阅者数量"""
        if user_id:
            return len(self._subscribers.get(user_id, []))
        return sum(len(v) for v in self._subscribers.values())


# 全局 SSE 管理器
sse_manager = SSEManager()


# ============================================================
# 任务状态推送器
# ============================================================

class TaskNotifier:
    """
    任务状态推送器

    统一通过 WebSocket 和 SSE 向前端推送 Celery 任务状态变更。
    """

    # 任务状态常量
    STATE_PENDING = "PENDING"
    STATE_STARTED = "STARTED"
    STATE_PROGRESS = "PROGRESS"
    STATE_SUCCESS = "SUCCESS"
    STATE_FAILURE = "FAILURE"
    STATE_REVOKED = "REVOKED"

    @staticmethod
    def notify(user_id: int, task_id: str, task_type: str,
               state: str, progress: int = 0, step: str = "",
               result: dict = None, error: str = None):
        """
        推送任务状态更新

        :param user_id: 目标用户ID
        :param task_id: Celery 任务ID
        :param task_type: 任务类型 (scraping/analysis/3d_generate/report)
        :param state: 任务状态 (PENDING/STARTED/PROGRESS/SUCCESS/FAILURE/REVOKED)
        :param progress: 进度百分比 (0-100)
        :param step: 当前步骤描述
        :param result: 任务结果 (成功时)
        :param error: 错误信息 (失败时)
        """
        event = {
            "type": "TASK_STATUS",
            "task_id": task_id,
            "task_type": task_type,
            "state": state,
            "progress": min(max(progress, 0), 100),
            "step": step,
            "timestamp": int(time.time()),
        }

        if result is not None:
            event["result"] = result
        if error is not None:
            event["error"] = error

        # 1. 通过 SSE 推送
        sse_manager.publish(user_id, event)

        # 2. 通过 WebSocket 推送（如果可用）
        try:
            from api.websocket_handler import broadcast_to_user
            broadcast_to_user(user_id, event)
        except (ImportError, Exception) as e:
            logger.debug(f"[TaskNotifier] WebSocket 推送跳过: {e}")

        logger.info(
            f"[TaskNotifier] user={user_id} task={task_id} "
            f"type={task_type} state={state} progress={progress}% step={step}"
        )

    @staticmethod
    def notify_started(user_id: int, task_id: str, task_type: str, step: str = "任务已开始"):
        """通知任务已开始"""
        TaskNotifier.notify(user_id, task_id, task_type,
                            state=TaskNotifier.STATE_STARTED, progress=0, step=step)

    @staticmethod
    def notify_progress(user_id: int, task_id: str, task_type: str,
                        progress: int, step: str = ""):
        """通知任务进度更新"""
        TaskNotifier.notify(user_id, task_id, task_type,
                            state=TaskNotifier.STATE_PROGRESS, progress=progress, step=step)

    @staticmethod
    def notify_success(user_id: int, task_id: str, task_type: str,
                       result: dict = None, step: str = "任务完成"):
        """通知任务成功完成"""
        TaskNotifier.notify(user_id, task_id, task_type,
                            state=TaskNotifier.STATE_SUCCESS, progress=100,
                            step=step, result=result)

    @staticmethod
    def notify_failure(user_id: int, task_id: str, task_type: str,
                       error: str = "任务执行失败", step: str = "任务失败"):
        """通知任务失败"""
        TaskNotifier.notify(user_id, task_id, task_type,
                            state=TaskNotifier.STATE_FAILURE, progress=0,
                            step=step, error=error)


# 全局推送器实例
notifier = TaskNotifier()
