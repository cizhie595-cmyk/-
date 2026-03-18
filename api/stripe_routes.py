"""
Coupang 选品系统 - Stripe 支付 API 路由
提供: Checkout Session 创建、Webhook 回调、客户门户
"""

from flask import Blueprint, request, jsonify, g
from auth.middleware import login_required
from monetization.stripe_handler import StripeHandler
from utils.logger import get_logger

logger = get_logger()

stripe_bp = Blueprint("stripe", __name__, url_prefix="/api/stripe")


# ============================================================
# POST /api/stripe/create-checkout-session - 创建支付会话
# ============================================================
@stripe_bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session(current_user):
    """
    创建 Stripe Checkout Session

    请求体 (JSON):
    {
        "plan_id": "orbit",           // orbit 或 moonshot
        "billing_cycle": "monthly",   // monthly 或 yearly
        "success_url": "...",         // 可选
        "cancel_url": "..."           // 可选
    }
    """
    if not StripeHandler.is_available():
        return jsonify({
            "success": False,
            "message": "支付功能暂未配置，请联系管理员",
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体不能为空"}), 400

    plan_id = data.get("plan_id", "")
    billing_cycle = data.get("billing_cycle", "monthly")

    if plan_id not in ("orbit", "moonshot"):
        return jsonify({"success": False, "message": "无效的订阅计划"}), 400
    if billing_cycle not in ("monthly", "yearly"):
        return jsonify({"success": False, "message": "无效的计费周期"}), 400

    user_id = current_user.get("user_id") or current_user.get("id")
    email = current_user.get("email", "")

    # 如果没有 email，尝试从数据库获取
    if not email:
        try:
            from auth.user_model import UserModel
            user = UserModel.get_by_id(user_id)
            email = user.get("email", "") if user else ""
        except Exception:
            pass

    result = StripeHandler.create_checkout_session(
        user_id=user_id,
        email=email,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
        success_url=data.get("success_url"),
        cancel_url=data.get("cancel_url"),
    )

    if result:
        return jsonify({
            "success": True,
            "session_id": result["session_id"],
            "checkout_url": result["checkout_url"],
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "创建支付会话失败，请稍后重试",
        }), 500


# ============================================================
# POST /api/stripe/webhook - Stripe Webhook 回调
# ============================================================
@stripe_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """
    Stripe Webhook 回调端点
    处理订阅生命周期事件
    """
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    event = StripeHandler.construct_webhook_event(payload, sig_header)
    if not event:
        return jsonify({"error": "Invalid signature"}), 400

    result = StripeHandler.handle_webhook_event(event)

    if result.get("handled"):
        logger.info(f"[Stripe Webhook] 处理成功: {result['action']}")
    else:
        logger.debug(f"[Stripe Webhook] 未处理: {result.get('action', 'unknown')}")

    return jsonify({"received": True}), 200


# ============================================================
# POST /api/stripe/customer-portal - 客户门户
# ============================================================
@stripe_bp.route("/customer-portal", methods=["POST"])
@login_required
def customer_portal(current_user):
    """
    创建 Stripe 客户门户会话
    用于用户自助管理订阅、查看发票、更新支付方式
    """
    if not StripeHandler.is_available():
        return jsonify({
            "success": False,
            "message": "支付功能暂未配置",
        }), 503

    user_id = current_user.get("user_id") or current_user.get("id")

    # 获取用户的 Stripe Customer ID
    try:
        from monetization.subscription import SubscriptionManager
        sub_info = SubscriptionManager.get_user_subscription(user_id)
        customer_id = sub_info.get("stripe_customer_id") if sub_info else None
    except Exception:
        customer_id = None

    if not customer_id:
        return jsonify({
            "success": False,
            "message": "未找到支付记录，请先订阅",
        }), 404

    portal_url = StripeHandler.create_customer_portal_session(
        customer_id=customer_id,
        return_url=request.json.get("return_url") if request.json else None,
    )

    if portal_url:
        return jsonify({
            "success": True,
            "portal_url": portal_url,
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "创建客户门户失败",
        }), 500


# ============================================================
# GET /api/stripe/config - 获取 Stripe 公钥配置
# ============================================================
@stripe_bp.route("/config", methods=["GET"])
def get_stripe_config():
    """返回 Stripe 公钥（前端初始化 Stripe.js 用）"""
    import os
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

    return jsonify({
        "success": True,
        "publishable_key": publishable_key,
        "available": StripeHandler.is_available(),
    }), 200
