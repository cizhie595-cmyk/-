"""
商业化模块 - REST API 路由

提供以下接口：
  GET  /api/subscription/plans        - 获取所有订阅计划
  GET  /api/subscription/me           - 获取当前用户订阅状态
  POST /api/subscription/upgrade      - 升级订阅
  POST /api/subscription/cancel       - 取消订阅
  GET  /api/subscription/usage        - 获取使用量统计
  POST /api/affiliate/link            - 生成 Affiliate 链接
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required, admin_required
from monetization.subscription import SubscriptionManager
from monetization.affiliate import AffiliateManager

monetization_bp = Blueprint("monetization", __name__)

affiliate_mgr = AffiliateManager()


# ============================================================
# 订阅管理
# ============================================================

@monetization_bp.route("/api/subscription/plans", methods=["GET"])
def get_plans():
    """获取所有订阅计划"""
    plans = SubscriptionManager.get_plans()
    return jsonify({"success": True, "plans": plans})


@monetization_bp.route("/api/subscription/me", methods=["GET"])
@login_required
def get_my_subscription(current_user):
    """获取当前用户的订阅状态"""
    sub = SubscriptionManager.get_user_subscription(current_user["id"])
    return jsonify({"success": True, "subscription": sub})


@monetization_bp.route("/api/subscription/upgrade", methods=["POST"])
@login_required
def upgrade_subscription(current_user):
    """升级订阅"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    plan_id = data.get("plan_id", "")
    billing_cycle = data.get("billing_cycle", "monthly")

    if not plan_id:
        return jsonify({"success": False, "message": "请指定订阅计划"}), 400

    # 注意：实际支付流程需要集成 Stripe/PayPal 等支付网关
    # 这里只处理订阅状态变更，支付验证需要额外实现
    payment_verified = data.get("payment_verified", False)

    if plan_id != "free" and not payment_verified:
        # 返回支付信息，前端引导用户完成支付
        from monetization.subscription import SUBSCRIPTION_PLANS
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        if not plan:
            return jsonify({"success": False, "message": "无效的计划"}), 400

        price = plan["price_yearly"] if billing_cycle == "yearly" else plan["price_monthly"]
        return jsonify({
            "success": False,
            "requires_payment": True,
            "plan": plan_id,
            "price": price,
            "currency": plan["currency"],
            "billing_cycle": billing_cycle,
            "message": "请完成支付后再确认升级",
        }), 402

    success, message = SubscriptionManager.upgrade_subscription(
        current_user["id"], plan_id, billing_cycle
    )

    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@monetization_bp.route("/api/subscription/cancel", methods=["POST"])
@login_required
def cancel_subscription(current_user):
    """取消订阅"""
    success, message = SubscriptionManager.cancel_subscription(current_user["id"])
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@monetization_bp.route("/api/subscription/usage", methods=["GET"])
@login_required
def get_usage(current_user):
    """获取使用量统计"""
    sub = SubscriptionManager.get_user_subscription(current_user["id"])
    features = sub["plan_info"].get("features", {})

    usage = {}
    for quota_type, limit in features.items():
        has_quota, remaining = SubscriptionManager.check_quota(
            current_user["id"], quota_type
        )
        usage[quota_type] = {
            "limit": limit,
            "remaining": remaining,
            "unlimited": limit == -1,
        }

    return jsonify({
        "success": True,
        "plan": sub["plan"],
        "usage": usage,
    })


# ============================================================
# Affiliate 链接
# ============================================================

@monetization_bp.route("/api/affiliate/link", methods=["POST"])
@login_required
def generate_affiliate_link(current_user):
    """生成 Affiliate 链接"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    asin = data.get("asin", "")
    marketplace = data.get("marketplace", "US")
    user_tag = data.get("user_tag", "")

    if not asin:
        return jsonify({"success": False, "message": "ASIN 不能为空"}), 400

    link = affiliate_mgr.generate_affiliate_link(asin, marketplace, user_tag)

    # 记录点击
    tag_used = user_tag or affiliate_mgr._get_system_tag(marketplace)
    affiliate_mgr.log_click(current_user["id"], asin, marketplace, tag_used)

    return jsonify({
        "success": True,
        "affiliate_link": link,
        "asin": asin,
        "marketplace": marketplace,
    })


@monetization_bp.route("/api/affiliate/batch", methods=["POST"])
@login_required
def batch_affiliate_links(current_user):
    """批量生成 Affiliate 链接"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    products = data.get("products", [])
    marketplace = data.get("marketplace", "US")
    user_tag = data.get("user_tag", "")

    processed = affiliate_mgr.inject_tags_batch(products, marketplace, user_tag)

    return jsonify({
        "success": True,
        "products": processed,
        "count": len(processed),
    })
