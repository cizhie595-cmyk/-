"""
Coupang 选品系统 - Celery 异步任务状态实时推送
通过 WebSocket 和 SSE (Server-Sent Events) 将任务进度推送至前端
支持多频道: tasks, notifications, prices, system
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
# SSE 事件管理器（支持多频道）
# ============================================================

class SSEManager:
    """
    Server-Sent Events 管理器

    支持多频道订阅:
    - tasks: 任务状态更新（爬取、分析、3D生成、报告）
    - notifications: 系统通知推送
    - prices: 价格变动推送
    - system: 系统级广播（维护通知、版本更新等）
    """

    DEFAULT_CHANNEL = "tasks"

    def __init__(self):
        # 结构: {channel: {user_id: [queue.Queue]}}
        self._channels = defaultdict(lambda: defaultdict(list))
        self._lock = threading.Lock()

    def subscribe(self, user_id: int, channel: str = None) -> queue.Queue:
        """用户订阅指定频道的事件流"""
        channel = channel or self.DEFAULT_CHANNEL
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._channels[channel][user_id].append(q)
        count = len(self._channels[channel][user_id])
        logger.debug(f"[SSE] User {user_id} subscribed to '{channel}' (total: {count})")
        return q

    def unsubscribe(self, user_id: int, q: queue.Queue, channel: str = None):
        """用户取消订阅指定频道"""
        channel = channel or self.DEFAULT_CHANNEL
        with self._lock:
            if channel in self._channels and user_id in self._channels[channel]:
                try:
                    self._channels[channel][user_id].remove(q)
                except ValueError:
                    pass
                if not self._channels[channel][user_id]:
                    del self._channels[channel][user_id]
        logger.debug(f"[SSE] User {user_id} unsubscribed from '{channel}'")

    def publish(self, user_id: int, event: dict, channel: str = None):
        """向用户的指定频道推送事件"""
        channel = channel or self.DEFAULT_CHANNEL
        with self._lock:
            queues = list(self._channels.get(channel, {}).get(user_id, []))

        dead_queues = []
        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead_queues.append(q)
                logger.warning(f"[SSE] Queue full for user {user_id} on '{channel}', dropping")

        # 清理满队列
        if dead_queues:
            with self._lock:
                for q in dead_queues:
                    try:
                        self._channels[channel][user_id].remove(q)
                    except (ValueError, KeyError):
                        pass

    def broadcast(self, event: dict, channel: str = None):
        """向指定频道的所有订阅者广播事件"""
        channel = channel or "system"
        with self._lock:
            all_users = dict(self._channels.get(channel, {}))

        for user_id, queues in all_users.items():
            for q in queues:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    logger.warning(f"[SSE] Broadcast queue full for user {user_id}")

    def get_subscriber_count(self, user_id: int = None, channel: str = None) -> int:
        """获取指定频道的订阅者数量"""
        channel = channel or self.DEFAULT_CHANNEL
        if user_id:
            return len(self._channels.get(channel, {}).get(user_id, []))
        return sum(len(v) for v in self._channels.get(channel, {}).values())

    def get_total_subscriber_count(self) -> int:
        """获取所有频道的总订阅者数量"""
        total = 0
        for channel_data in self._channels.values():
            total += sum(len(v) for v in channel_data.values())
        return total


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

        # 1. 通过 SSE 推送（tasks 频道）
        sse_manager.publish(user_id, event, channel="tasks")

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

    @staticmethod
    def notify_notification(user_id: int, title: str, message: str,
                            notification_type: str = "info", link: str = None):
        """推送系统通知到 notifications 频道"""
        event = {
            "type": "NOTIFICATION",
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "timestamp": int(time.time()),
        }
        if link:
            event["link"] = link
        sse_manager.publish(user_id, event, channel="notifications")

    @staticmethod
    def notify_price_change(user_id: int, asin: str, product_name: str,
                            old_price: float, new_price: float, currency: str = "USD"):
        """推送价格变动到 prices 频道"""
        change_pct = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
        event = {
            "type": "PRICE_CHANGE",
            "asin": asin,
            "product_name": product_name,
            "old_price": old_price,
            "new_price": new_price,
            "currency": currency,
            "change_percent": round(change_pct, 2),
            "direction": "up" if new_price > old_price else "down",
            "timestamp": int(time.time()),
        }
        sse_manager.publish(user_id, event, channel="prices")


# 全局推送器实例
notifier = TaskNotifier()
