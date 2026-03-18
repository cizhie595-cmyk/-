"""
Coupang 选品系统 - Server-Sent Events (SSE) 路由
提供: 任务状态实时推送流、通知推送、价格变动推送
支持: 多频道订阅、心跳保活、Last-Event-ID 断线重连
"""

import json
import time
from flask import Blueprint, Response, request, stream_with_context
from auth.middleware import login_required
from utils.task_notifier import sse_manager
from utils.logger import get_logger

logger = get_logger()

sse_bp = Blueprint("sse", __name__, url_prefix="/api/sse")

# 支持的频道列表
VALID_CHANNELS = {"tasks", "notifications", "prices", "system"}


@sse_bp.route("/tasks", methods=["GET"])
@login_required
def task_events_stream(current_user):
    """
    SSE 端点: 实时推送任务状态更新

    前端使用方式:
        const es = new EventSource('/api/sse/tasks?token=xxx');
        es.addEventListener('task_status', (e) => {
            const data = JSON.parse(e.data);
            console.log(data.task_id, data.state, data.progress);
        });
    """
    user_id = current_user.get("user_id") or current_user.get("sub")
    last_event_id = request.headers.get("Last-Event-ID")

    def generate():
        q = sse_manager.subscribe(user_id)
        event_counter = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        try:
            # 发送连接成功事件
            event_counter += 1
            yield f"id: {event_counter}\nevent: connected\ndata: {json.dumps({'user_id': user_id, 'ts': int(time.time()), 'channel': 'tasks'})}\n\n"

            while True:
                try:
                    # 等待事件（25秒超时发心跳）
                    event = q.get(timeout=25)
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: task_status\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception:
                    # 超时，发送心跳保持连接
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: heartbeat\ndata: {json.dumps({'ts': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_manager.unsubscribe(user_id, q)
            logger.debug(f"[SSE] Task stream closed for user {user_id}")

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/notifications", methods=["GET"])
@login_required
def notification_events_stream(current_user):
    """
    SSE 端点: 实时推送通知

    前端使用方式:
        const es = new EventSource('/api/sse/notifications?token=xxx');
        es.addEventListener('notification', (e) => {
            const data = JSON.parse(e.data);
            showToast(data.title, data.message);
        });
    """
    user_id = current_user.get("user_id") or current_user.get("sub")
    last_event_id = request.headers.get("Last-Event-ID")

    def generate():
        q = sse_manager.subscribe(user_id, channel="notifications")
        event_counter = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        try:
            event_counter += 1
            yield f"id: {event_counter}\nevent: connected\ndata: {json.dumps({'user_id': user_id, 'ts': int(time.time()), 'channel': 'notifications'})}\n\n"

            while True:
                try:
                    event = q.get(timeout=25)
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: notification\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception:
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: heartbeat\ndata: {json.dumps({'ts': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_manager.unsubscribe(user_id, q, channel="notifications")
            logger.debug(f"[SSE] Notification stream closed for user {user_id}")

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/prices", methods=["GET"])
@login_required
def price_events_stream(current_user):
    """
    SSE 端点: 实时推送价格变动

    前端使用方式:
        const es = new EventSource('/api/sse/prices?token=xxx');
        es.addEventListener('price_change', (e) => {
            const data = JSON.parse(e.data);
            console.log(data.asin, data.old_price, data.new_price);
        });
    """
    user_id = current_user.get("user_id") or current_user.get("sub")
    last_event_id = request.headers.get("Last-Event-ID")

    def generate():
        q = sse_manager.subscribe(user_id, channel="prices")
        event_counter = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        try:
            event_counter += 1
            yield f"id: {event_counter}\nevent: connected\ndata: {json.dumps({'user_id': user_id, 'ts': int(time.time()), 'channel': 'prices'})}\n\n"

            while True:
                try:
                    event = q.get(timeout=25)
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: price_change\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception:
                    event_counter += 1
                    yield f"id: {event_counter}\nevent: heartbeat\ndata: {json.dumps({'ts': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_manager.unsubscribe(user_id, q, channel="prices")
            logger.debug(f"[SSE] Price stream closed for user {user_id}")

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/status", methods=["GET"])
@login_required
def sse_status(current_user):
    """获取当前 SSE 连接状态（所有频道）"""
    user_id = current_user.get("user_id") or current_user.get("sub")
    return {
        "success": True,
        "user_id": user_id,
        "channels": {
            "tasks": sse_manager.get_subscriber_count(user_id, channel="tasks"),
            "notifications": sse_manager.get_subscriber_count(user_id, channel="notifications"),
            "prices": sse_manager.get_subscriber_count(user_id, channel="prices"),
        },
        "total_subscribers": sse_manager.get_total_subscriber_count(),
    }, 200
