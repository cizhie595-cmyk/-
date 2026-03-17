"""
"登月计划" 阶梯付费订阅系统

三个等级：
  1. Free（免费版）       - 基础功能体验
  2. Orbit（轨道版）      - 专业卖家日常使用
  3. Moonshot（登月版）   - 高级卖家/团队全功能

每个等级有不同的功能权限和使用配额。
"""

import json
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 订阅计划定义
# ============================================================

SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "display_name": "免费版",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "USD",
        "features": {
            "keyword_searches_per_day": 5,
            "product_analyses_per_day": 10,
            "ai_analyses_per_day": 3,
            "report_exports_per_month": 2,
            "model_3d_generations_per_month": 0,
            "saved_projects": 3,
            "team_members": 1,
            "data_retention_days": 7,
            "api_rate_limit_per_min": 10,
        },
        "modules": {
            "search_crawler": True,
            "data_filter": True,
            "deep_crawler": False,
            "ai_review_analysis": True,      # 有限次数
            "ai_detail_analysis": False,
            "ocr_extraction": False,
            "model_3d": False,
            "category_analysis": True,        # 基础版
            "profit_calculator": True,
            "risk_analysis": False,
            "report_generator": True,         # 基础报告
            "affiliate_links": True,
            "source_matching_1688": False,
        },
        "description": "适合初次体验的新手卖家，了解系统核心功能",
    },

    "orbit": {
        "name": "Orbit",
        "display_name": "轨道版",
        "price_monthly": 29.99,
        "price_yearly": 299.99,
        "currency": "USD",
        "features": {
            "keyword_searches_per_day": 50,
            "product_analyses_per_day": 100,
            "ai_analyses_per_day": 30,
            "report_exports_per_month": 20,
            "model_3d_generations_per_month": 5,
            "saved_projects": 20,
            "team_members": 3,
            "data_retention_days": 90,
            "api_rate_limit_per_min": 60,
        },
        "modules": {
            "search_crawler": True,
            "data_filter": True,
            "deep_crawler": True,
            "ai_review_analysis": True,
            "ai_detail_analysis": True,
            "ocr_extraction": True,
            "model_3d": True,                 # 有限次数
            "category_analysis": True,
            "profit_calculator": True,
            "risk_analysis": True,
            "report_generator": True,
            "affiliate_links": True,
            "source_matching_1688": True,
        },
        "description": "适合专业卖家日常选品使用，覆盖完整分析流程",
    },

    "moonshot": {
        "name": "Moonshot",
        "display_name": "登月版",
        "price_monthly": 99.99,
        "price_yearly": 999.99,
        "currency": "USD",
        "features": {
            "keyword_searches_per_day": -1,      # -1 = 无限制
            "product_analyses_per_day": -1,
            "ai_analyses_per_day": -1,
            "report_exports_per_month": -1,
            "model_3d_generations_per_month": 50,
            "saved_projects": -1,
            "team_members": 10,
            "data_retention_days": 365,
            "api_rate_limit_per_min": 200,
        },
        "modules": {
            "search_crawler": True,
            "data_filter": True,
            "deep_crawler": True,
            "ai_review_analysis": True,
            "ai_detail_analysis": True,
            "ocr_extraction": True,
            "model_3d": True,
            "category_analysis": True,
            "profit_calculator": True,
            "risk_analysis": True,
            "report_generator": True,
            "affiliate_links": True,
            "source_matching_1688": True,
        },
        "extras": [
            "优先客服支持",
            "自定义报告模板",
            "API 高频调用",
            "多人协作",
            "数据导出无限制",
            "专属选品顾问（季度）",
        ],
        "description": "适合高级卖家和团队，全功能无限制使用",
    },
}


class SubscriptionManager:
    """
    订阅管理器

    负责：
      1. 用户订阅状态管理
      2. 功能权限检查
      3. 使用配额追踪
      4. 订阅升级/降级
    """

    @staticmethod
    def get_plans() -> list[dict]:
        """获取所有订阅计划（供前端展示）"""
        plans = []
        for plan_id, plan in SUBSCRIPTION_PLANS.items():
            plans.append({
                "id": plan_id,
                "name": plan["name"],
                "display_name": plan["display_name"],
                "price_monthly": plan["price_monthly"],
                "price_yearly": plan["price_yearly"],
                "currency": plan["currency"],
                "features": plan["features"],
                "modules": plan["modules"],
                "description": plan["description"],
                "extras": plan.get("extras", []),
            })
        return plans

    @staticmethod
    def get_user_subscription(user_id: int) -> dict:
        """
        获取用户当前的订阅状态。

        :param user_id: 用户 ID
        :return: 订阅信息
        """
        from database.connection import db

        try:
            sql = """
                SELECT subscription_plan, subscription_expires_at,
                       subscription_started_at, billing_cycle
                FROM users WHERE id = %s
            """
            row = db.fetch_one(sql, (user_id,))

            if not row or not row.get("subscription_plan"):
                return {
                    "plan": "free",
                    "plan_info": SUBSCRIPTION_PLANS["free"],
                    "is_active": True,
                    "expires_at": None,
                }

            plan_id = row["subscription_plan"]
            expires_at = row.get("subscription_expires_at")

            # 检查是否过期
            is_active = True
            if expires_at and isinstance(expires_at, datetime):
                is_active = expires_at > datetime.now()

            if not is_active:
                plan_id = "free"  # 过期自动降级为免费版

            return {
                "plan": plan_id,
                "plan_info": SUBSCRIPTION_PLANS.get(plan_id, SUBSCRIPTION_PLANS["free"]),
                "is_active": is_active,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "started_at": row.get("subscription_started_at", "").isoformat()
                    if row.get("subscription_started_at") else None,
                "billing_cycle": row.get("billing_cycle", "monthly"),
            }

        except Exception as e:
            logger.error(f"[订阅] 获取订阅状态失败: {e}")
            return {
                "plan": "free",
                "plan_info": SUBSCRIPTION_PLANS["free"],
                "is_active": True,
                "expires_at": None,
            }

    @staticmethod
    def check_module_access(user_id: int, module_name: str) -> tuple[bool, str]:
        """
        检查用户是否有权限使用某个功能模块。

        :param user_id: 用户 ID
        :param module_name: 模块名称
        :return: (是否有权限, 提示信息)
        """
        sub = SubscriptionManager.get_user_subscription(user_id)
        plan_info = sub["plan_info"]
        modules = plan_info.get("modules", {})

        if modules.get(module_name, False):
            return True, ""

        # 找到最低可用的计划
        for plan_id, plan in SUBSCRIPTION_PLANS.items():
            if plan["modules"].get(module_name, False):
                return False, (
                    f"该功能需要 {plan['display_name']} 及以上版本。"
                    f"当前版本: {plan_info['display_name']}，"
                    f"请升级到 {plan['display_name']}（${plan['price_monthly']}/月）"
                )

        return False, "该功能暂不可用"

    @staticmethod
    def check_quota(user_id: int, quota_type: str) -> tuple[bool, int]:
        """
        检查用户的使用配额。

        :param user_id: 用户 ID
        :param quota_type: 配额类型（如 keyword_searches_per_day）
        :return: (是否还有配额, 剩余次数)
        """
        sub = SubscriptionManager.get_user_subscription(user_id)
        plan_info = sub["plan_info"]
        features = plan_info.get("features", {})

        limit = features.get(quota_type, 0)

        if limit == -1:
            return True, -1  # 无限制

        # 查询今日已使用次数
        used = SubscriptionManager._get_usage_count(user_id, quota_type)
        remaining = max(0, limit - used)

        return remaining > 0, remaining

    @staticmethod
    def record_usage(user_id: int, quota_type: str, count: int = 1):
        """记录使用量"""
        from database.connection import db

        try:
            sql = """
                INSERT INTO usage_records (user_id, quota_type, count, recorded_date)
                VALUES (%s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE count = count + %s
            """
            db.execute(sql, (user_id, quota_type, count, count))
        except Exception as e:
            logger.error(f"[配额] 记录使用量失败: {e}")

    @staticmethod
    def upgrade_subscription(user_id: int, plan_id: str,
                              billing_cycle: str = "monthly") -> tuple[bool, str]:
        """
        升级用户订阅。

        :param user_id: 用户 ID
        :param plan_id: 目标计划
        :param billing_cycle: 计费周期 monthly/yearly
        :return: (是否成功, 提示信息)
        """
        if plan_id not in SUBSCRIPTION_PLANS:
            return False, f"无效的订阅计划: {plan_id}"

        plan = SUBSCRIPTION_PLANS[plan_id]

        # 计算到期时间
        now = datetime.now()
        if billing_cycle == "yearly":
            expires_at = now + timedelta(days=365)
        else:
            expires_at = now + timedelta(days=30)

        from database.connection import db

        try:
            sql = """
                UPDATE users SET
                    subscription_plan = %s,
                    subscription_started_at = %s,
                    subscription_expires_at = %s,
                    billing_cycle = %s
                WHERE id = %s
            """
            db.execute(sql, (plan_id, now, expires_at, billing_cycle, user_id))

            # 记录订阅变更日志
            SubscriptionManager._log_subscription_change(
                user_id, plan_id, billing_cycle, now, expires_at
            )

            logger.info(
                f"[订阅] 升级成功: user_id={user_id}, "
                f"plan={plan_id}, expires={expires_at}"
            )
            return True, (
                f"订阅升级成功！当前计划: {plan['display_name']}，"
                f"有效期至: {expires_at.strftime('%Y-%m-%d')}"
            )

        except Exception as e:
            logger.error(f"[订阅] 升级失败: {e}")
            return False, f"订阅升级失败: {str(e)}"

    @staticmethod
    def cancel_subscription(user_id: int) -> tuple[bool, str]:
        """取消订阅（到期后自动降级为免费版）"""
        from database.connection import db

        try:
            # 不立即降级，而是标记为不续费
            sql = """
                UPDATE users SET billing_cycle = 'cancelled' WHERE id = %s
            """
            db.execute(sql, (user_id,))

            sub = SubscriptionManager.get_user_subscription(user_id)
            expires = sub.get("expires_at", "")

            return True, f"订阅已取消，当前计划将在 {expires} 到期后降级为免费版"

        except Exception as e:
            logger.error(f"[订阅] 取消失败: {e}")
            return False, f"取消失败: {str(e)}"

    # ============================================================
    # 内部方法
    # ============================================================

    @staticmethod
    def _get_usage_count(user_id: int, quota_type: str) -> int:
        """获取今日使用量"""
        from database.connection import db

        try:
            sql = """
                SELECT COALESCE(SUM(count), 0) as total
                FROM usage_records
                WHERE user_id = %s AND quota_type = %s AND recorded_date = CURDATE()
            """
            row = db.fetch_one(sql, (user_id, quota_type))
            return row["total"] if row else 0
        except Exception:
            return 0

    @staticmethod
    def _log_subscription_change(user_id: int, plan_id: str,
                                  billing_cycle: str,
                                  started_at: datetime,
                                  expires_at: datetime):
        """记录订阅变更日志"""
        from database.connection import db

        try:
            sql = """
                INSERT INTO subscription_logs
                    (user_id, plan_id, billing_cycle, started_at, expires_at, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            db.execute(sql, (user_id, plan_id, billing_cycle, started_at, expires_at))
        except Exception as e:
            logger.error(f"[订阅] 记录日志失败: {e}")
