"""
Coupang 选品系统 - API 请求限流中间件
基于 Flask-Limiter 实现，根据用户订阅等级动态调整限流阈值
"""
import os
from flask import Flask, request, jsonify, g
from utils.logger import get_logger

logger = get_logger()

# 尝试导入 Flask-Limiter
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    logger.warning("[RateLimiter] Flask-Limiter 未安装，限流功能不可用。"
                   "请运行: pip install Flask-Limiter")


def _get_user_identifier():
    """
    获取限流标识符：
    - 已认证用户：使用 user_id
    - 未认证用户：使用 IP 地址
    """
    current_user = getattr(g, "current_user", None)
    if current_user:
        user_id = current_user.get("user_id") or current_user.get("sub")
        if user_id:
            return f"user:{user_id}"
    return f"ip:{get_remote_address()}"


def _get_user_rate_limit():
    """
    根据用户订阅等级返回动态限流字符串
    Free: 10/minute, Orbit: 60/minute, Moonshot: 200/minute
    未认证: 10/minute
    """
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return "10/minute"

    user_id = current_user.get("user_id") or current_user.get("sub")
    if not user_id:
        return "10/minute"

    try:
        from monetization.subscription import SubscriptionManager
        sub_info = SubscriptionManager.get_user_subscription(user_id)
        if sub_info and sub_info.get("plan_info"):
            rate_limit = sub_info["plan_info"].get("api_rate_limit_per_min", 10)
            return f"{rate_limit}/minute"
    except Exception as e:
        logger.debug(f"[RateLimiter] 获取订阅信息失败: {e}")

    return "10/minute"


def init_rate_limiter(app: Flask):
    """
    初始化限流中间件

    :param app: Flask 应用实例
    :return: Limiter 实例或 None
    """
    if not LIMITER_AVAILABLE:
        logger.warning("[RateLimiter] Flask-Limiter 不可用，跳过限流初始化")
        return None

    # Redis 存储后端（与 Celery 共用 Redis）
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", redis_url)

    try:
        limiter = Limiter(
            app=app,
            key_func=_get_user_identifier,
            default_limits=["100/minute"],  # 全局默认限流
            storage_uri=storage_uri,
            strategy="fixed-window",
            headers_enabled=True,  # 返回 X-RateLimit-* 响应头
        )

        # 自定义超限响应
        @app.errorhandler(429)
        def rate_limit_exceeded(e):
            return jsonify({
                "success": False,
                "error": "rate_limit_exceeded",
                "message": "请求过于频繁，请稍后再试",
                "retry_after": e.description if hasattr(e, 'description') else "60",
            }), 429

        logger.info("[RateLimiter] 限流中间件初始化成功")
        return limiter

    except Exception as e:
        logger.error(f"[RateLimiter] 初始化失败: {e}")
        # 降级：不使用 Redis，使用内存存储
        try:
            limiter = Limiter(
                app=app,
                key_func=_get_user_identifier,
                default_limits=["100/minute"],
                storage_uri="memory://",
                strategy="fixed-window",
                headers_enabled=True,
            )

            @app.errorhandler(429)
            def rate_limit_exceeded_fallback(e):
                return jsonify({
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "message": "请求过于频繁，请稍后再试",
                }), 429

            logger.warning("[RateLimiter] Redis 不可用，降级为内存存储")
            return limiter
        except Exception as e2:
            logger.error(f"[RateLimiter] 降级初始化也失败: {e2}")
            return None


def apply_dynamic_limits(limiter):
    """
    为特定路由应用动态限流规则

    :param limiter: Limiter 实例
    """
    if not limiter:
        return

    # 爬虫相关 API 更严格的限流
    scraper_limit = limiter.shared_limit(
        "5/minute",
        scope="scraper_api",
        key_func=_get_user_identifier,
    )

    # 认证相关 API 限流（防止暴力破解）
    auth_limit = limiter.shared_limit(
        "20/minute",
        scope="auth_api",
        key_func=get_remote_address,
    )

    return {
        "scraper": scraper_limit,
        "auth": auth_limit,
    }
