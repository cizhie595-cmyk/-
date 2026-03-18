"""
Coupang 选品系统 - Server-Sent Events (SSE) 路由
提供: 任务状态实时推送流
"""

import json
import time
from flask import Blueprint, Response, request, stream_with_context
from auth.middleware import login_required
from utils.task_notifier import sse_manager
from utils.logger import get_logger

logger = get_logger()

sse_bp = Blueprint("sse", __name__, url_prefix="/api/sse")


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

    def generate():
        q = sse_manager.subscribe(user_id)
        try:
            # 发送连接成功事件
            yield f"event: connected\ndata: {json.dumps({'user_id': user_id, 'ts': int(time.time())})}\n\n"

            while True:
                try:
                    # 等待事件（30秒超时发心跳）
                    event = q.get(timeout=30)
                    yield f"event: task_status\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception:
                    # 超时，发送心跳保持连接
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_manager.unsubscribe(user_id, q)
            logger.debug(f"[SSE] Stream closed for user {user_id}")

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
    """获取当前 SSE 连接状态"""
    user_id = current_user.get("user_id") or current_user.get("sub")
    return {
        "success": True,
        "user_id": user_id,
        "subscriber_count": sse_manager.get_subscriber_count(user_id),
        "total_subscribers": sse_manager.get_subscriber_count(),
    }, 200
