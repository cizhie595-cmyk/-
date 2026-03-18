"""
Coupang 选品系统 - APM 性能监控集成
支持: Prometheus 指标 + 请求追踪 + 慢查询检测 + 健康检查
"""

import os
import time
import threading
import functools
from datetime import datetime
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 指标收集器
# ============================================================

class MetricsCollector:
    """应用性能指标收集器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._reset_metrics()

    def _reset_metrics(self):
        """重置所有指标"""
        self.request_count = defaultdict(int)           # {endpoint: count}
        self.request_duration = defaultdict(list)        # {endpoint: [durations]}
        self.error_count = defaultdict(int)              # {endpoint: count}
        self.status_codes = defaultdict(int)             # {status_code: count}
        self.active_requests = 0
        self.total_requests = 0
        self.db_query_count = 0
        self.db_query_duration = 0.0
        self.slow_queries = []                           # [{query, duration, timestamp}]
        self.celery_task_count = defaultdict(int)        # {task_name: count}
        self.celery_task_duration = defaultdict(list)    # {task_name: [durations]}
        self.start_time = time.time()

    def record_request(self, endpoint: str, method: str, status_code: int,
                       duration: float):
        """记录 HTTP 请求"""
        with self._lock:
            key = f"{method} {endpoint}"
            self.request_count[key] += 1
            self.request_duration[key].append(duration)
            self.status_codes[status_code] += 1
            self.total_requests += 1

            if status_code >= 400:
                self.error_count[key] += 1

            # 保留最近 1000 条耗时记录
            if len(self.request_duration[key]) > 1000:
                self.request_duration[key] = self.request_duration[key][-500:]

    def record_db_query(self, query: str, duration: float):
        """记录数据库查询"""
        with self._lock:
            self.db_query_count += 1
            self.db_query_duration += duration

            # 慢查询检测 (>1s)
            slow_threshold = float(os.getenv("APM_SLOW_QUERY_THRESHOLD", "1.0"))
            if duration > slow_threshold:
                self.slow_queries.append({
                    "query": query[:200],
                    "duration_ms": round(duration * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                })
                # 保留最近 50 条慢查询
                if len(self.slow_queries) > 50:
                    self.slow_queries = self.slow_queries[-50:]

                logger.warning(
                    f"[APM] 慢查询检测: {duration*1000:.0f}ms - {query[:100]}"
                )

    def record_celery_task(self, task_name: str, duration: float, success: bool):
        """记录 Celery 任务"""
        with self._lock:
            self.celery_task_count[task_name] += 1
            self.celery_task_duration[task_name].append(duration)

    def increment_active(self):
        with self._lock:
            self.active_requests += 1

    def decrement_active(self):
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)

    def get_metrics(self) -> dict:
        """获取所有指标"""
        with self._lock:
            uptime = time.time() - self.start_time

            # 计算请求延迟统计
            endpoint_stats = {}
            for endpoint, durations in self.request_duration.items():
                if durations:
                    sorted_d = sorted(durations)
                    endpoint_stats[endpoint] = {
                        "count": self.request_count[endpoint],
                        "errors": self.error_count.get(endpoint, 0),
                        "avg_ms": round(sum(sorted_d) / len(sorted_d) * 1000, 2),
                        "p50_ms": round(sorted_d[len(sorted_d) // 2] * 1000, 2),
                        "p95_ms": round(sorted_d[int(len(sorted_d) * 0.95)] * 1000, 2),
                        "p99_ms": round(sorted_d[int(len(sorted_d) * 0.99)] * 1000, 2),
                        "max_ms": round(max(sorted_d) * 1000, 2),
                    }

            return {
                "uptime_seconds": round(uptime, 0),
                "total_requests": self.total_requests,
                "active_requests": self.active_requests,
                "requests_per_second": round(self.total_requests / max(uptime, 1), 2),
                "status_codes": dict(self.status_codes),
                "endpoints": endpoint_stats,
                "database": {
                    "total_queries": self.db_query_count,
                    "total_duration_ms": round(self.db_query_duration * 1000, 2),
                    "avg_query_ms": round(
                        (self.db_query_duration / max(self.db_query_count, 1)) * 1000, 2
                    ),
                    "slow_queries": self.slow_queries[-10:],
                },
                "celery": {
                    "tasks": {
                        name: {
                            "count": self.celery_task_count[name],
                            "avg_ms": round(
                                sum(durs) / len(durs) * 1000, 2
                            ) if durs else 0,
                        }
                        for name, durs in self.celery_task_duration.items()
                    },
                },
            }

    def get_prometheus_metrics(self) -> str:
        """生成 Prometheus 格式的指标"""
        lines = []
        metrics = self.get_metrics()

        # 基础指标
        lines.append(f'# HELP avst_uptime_seconds Application uptime in seconds')
        lines.append(f'# TYPE avst_uptime_seconds gauge')
        lines.append(f'avst_uptime_seconds {metrics["uptime_seconds"]}')

        lines.append(f'# HELP avst_requests_total Total HTTP requests')
        lines.append(f'# TYPE avst_requests_total counter')
        lines.append(f'avst_requests_total {metrics["total_requests"]}')

        lines.append(f'# HELP avst_active_requests Current active requests')
        lines.append(f'# TYPE avst_active_requests gauge')
        lines.append(f'avst_active_requests {metrics["active_requests"]}')

        lines.append(f'# HELP avst_rps Requests per second')
        lines.append(f'# TYPE avst_rps gauge')
        lines.append(f'avst_rps {metrics["requests_per_second"]}')

        # 状态码
        lines.append(f'# HELP avst_http_status_total HTTP responses by status code')
        lines.append(f'# TYPE avst_http_status_total counter')
        for code, count in metrics["status_codes"].items():
            lines.append(f'avst_http_status_total{{code="{code}"}} {count}')

        # 端点延迟
        lines.append(f'# HELP avst_request_duration_ms Request duration in milliseconds')
        lines.append(f'# TYPE avst_request_duration_ms summary')
        for endpoint, stats in metrics["endpoints"].items():
            safe_ep = endpoint.replace('"', '\\"')
            lines.append(f'avst_request_duration_ms{{endpoint="{safe_ep}",quantile="0.5"}} {stats["p50_ms"]}')
            lines.append(f'avst_request_duration_ms{{endpoint="{safe_ep}",quantile="0.95"}} {stats["p95_ms"]}')
            lines.append(f'avst_request_duration_ms{{endpoint="{safe_ep}",quantile="0.99"}} {stats["p99_ms"]}')

        # 数据库
        lines.append(f'# HELP avst_db_queries_total Total database queries')
        lines.append(f'# TYPE avst_db_queries_total counter')
        lines.append(f'avst_db_queries_total {metrics["database"]["total_queries"]}')

        lines.append(f'# HELP avst_db_query_avg_ms Average query duration')
        lines.append(f'# TYPE avst_db_query_avg_ms gauge')
        lines.append(f'avst_db_query_avg_ms {metrics["database"]["avg_query_ms"]}')

        return "\n".join(lines) + "\n"


# 全局实例
metrics = MetricsCollector()


# ============================================================
# Flask 中间件
# ============================================================

def init_apm(app):
    """
    初始化 APM 中间件

    在 Flask app 上注册 before/after request hooks
    """
    if not os.getenv("APM_ENABLED", "true").lower() == "true":
        logger.info("[APM] APM 已禁用")
        return

    @app.before_request
    def _apm_before():
        from flask import request as req, g
        g.apm_start_time = time.time()
        metrics.increment_active()

    @app.after_request
    def _apm_after(response):
        from flask import request as req, g
        start = getattr(g, "apm_start_time", None)
        if start:
            duration = time.time() - start
            endpoint = req.endpoint or req.path
            metrics.record_request(
                endpoint=endpoint,
                method=req.method,
                status_code=response.status_code,
                duration=duration,
            )
        metrics.decrement_active()
        return response

    logger.info("[APM] APM 性能监控已启用")


# ============================================================
# 装饰器: 追踪函数执行时间
# ============================================================

def trace(name: str = None):
    """
    函数执行时间追踪装饰器

    用法:
        @trace("my_function")
        def my_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            fn_name = name or f"{func.__module__}.{func.__name__}"
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if duration > 1.0:
                    logger.info(f"[APM] {fn_name}: {duration*1000:.0f}ms")
        return wrapper
    return decorator


# ============================================================
# 健康检查
# ============================================================

def get_health_status() -> dict:
    """获取系统健康状态"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
    }

    # 检查数据库
    try:
        from database.connection import db
        start = time.time()
        db.fetch_one("SELECT 1")
        db_latency = (time.time() - start) * 1000
        status["checks"]["database"] = {
            "status": "up",
            "latency_ms": round(db_latency, 2),
        }
    except Exception as e:
        status["checks"]["database"] = {"status": "down", "error": str(e)}
        status["status"] = "degraded"

    # 检查 Redis
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        start = time.time()
        r.ping()
        redis_latency = (time.time() - start) * 1000
        status["checks"]["redis"] = {
            "status": "up",
            "latency_ms": round(redis_latency, 2),
        }
    except Exception as e:
        status["checks"]["redis"] = {"status": "down", "error": str(e)}
        status["status"] = "degraded"

    # 检查磁盘空间
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        disk_pct = (used / total) * 100
        status["checks"]["disk"] = {
            "status": "up" if disk_pct < 90 else "warning",
            "usage_percent": round(disk_pct, 1),
            "free_gb": round(free / (1024**3), 2),
        }
        if disk_pct >= 90:
            status["status"] = "degraded"
    except Exception:
        pass

    return status
