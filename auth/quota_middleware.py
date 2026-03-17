"""
额度校验中间件
在用户触发消耗额度的操作前拦截检查，对应 PRD 2.3 权限与额度校验
"""

import functools
from flask import jsonify, g

from monetization.subscription import SubscriptionManager


def quota_required(quota_type: str, count: int = 1):
    """
    装饰器：检查用户是否有足够的配额执行操作

    :param quota_type: 配额类型，如 'scrape', 'analysis', '3d_generate', 'render_video'
    :param count: 本次操作消耗的额度数量
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, "user_id", None)
            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "unauthorized",
                    "message": "请先登录",
                }), 401

            # 检查额度
            has_quota, remaining = SubscriptionManager.check_quota(user_id, quota_type)
            if not has_quota:
                plan = SubscriptionManager.get_user_subscription(user_id)
                return jsonify({
                    "success": False,
                    "error": "quota_exceeded",
                    "message": "当前版本额度已耗尽",
                    "data": {
                        "quota_type": quota_type,
                        "remaining": remaining,
                        "current_plan": plan.get("plan_id", "free"),
                        "upgrade_url": "/settings/subscription",
                    },
                }), 403

            # 检查模块访问权限
            module_map = {
                "scrape": "scraping",
                "analysis": "ai_analysis",
                "3d_generate": "3d_generation",
                "render_video": "video_render",
            }
            module_name = module_map.get(quota_type)
            if module_name:
                has_access, msg = SubscriptionManager.check_module_access(user_id, module_name)
                if not has_access:
                    return jsonify({
                        "success": False,
                        "error": "module_locked",
                        "message": msg,
                        "data": {
                            "module": module_name,
                            "upgrade_url": "/settings/subscription",
                        },
                    }), 403

            # 执行原函数
            result = f(*args, **kwargs)

            # 操作成功后记录使用量
            # 注意：只有在返回成功响应时才扣减额度
            if isinstance(result, tuple):
                response, status_code = result
            else:
                response = result
                status_code = 200

            if 200 <= status_code < 300:
                try:
                    SubscriptionManager.record_usage(user_id, quota_type, count)
                except Exception:
                    pass  # 记录失败不影响主流程

            return result

        return decorated
    return decorator


def check_quota_api(user_id: int, quota_type: str) -> dict:
    """
    检查用户配额的工具函数（供 API 调用）

    :return: 包含 used / limit / remaining 的字典
    """
    try:
        has_quota, remaining = SubscriptionManager.check_quota(user_id, quota_type)
        plan = SubscriptionManager.get_user_subscription(user_id)
        usage = SubscriptionManager.get_usage(user_id, quota_type) if hasattr(SubscriptionManager, 'get_usage') else {}

        used = usage.get("used", 0) if usage else 0
        limit_val = used + remaining

        return {
            "has_quota": has_quota,
            "used": used,
            "limit": limit_val,
            "remaining": remaining,
            "plan_id": plan.get("plan_id", "free") if plan else "free",
            "plan_name": plan.get("plan_name", "免费版") if plan else "免费版",
        }
    except Exception:
        return {
            "has_quota": True,
            "used": 0,
            "limit": 999,
            "remaining": 999,
            "plan_id": "free",
            "plan_name": "免费版",
        }
