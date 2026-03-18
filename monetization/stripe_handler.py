"""
Coupang 选品系统 - Stripe 支付网关集成
提供: Checkout Session 创建、Webhook 处理、订阅生命周期管理
"""
import os
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

# Stripe 配置
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")

# 尝试导入 Stripe SDK
try:
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    STRIPE_AVAILABLE = bool(STRIPE_SECRET_KEY)
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("[Stripe] stripe SDK 未安装，请运行: pip install stripe")

# 订阅计划到 Stripe Price ID 的映射
# 在 Stripe Dashboard 中创建 Product 和 Price 后填入
PLAN_PRICE_MAP = {
    "orbit": {
        "monthly": os.getenv("STRIPE_PRICE_ORBIT_MONTHLY", ""),
        "yearly": os.getenv("STRIPE_PRICE_ORBIT_YEARLY", ""),
    },
    "moonshot": {
        "monthly": os.getenv("STRIPE_PRICE_MOONSHOT_MONTHLY", ""),
        "yearly": os.getenv("STRIPE_PRICE_MOONSHOT_YEARLY", ""),
    },
}


class StripeHandler:
    """Stripe 支付处理器"""

    @staticmethod
    def is_available() -> bool:
        """检查 Stripe 是否可用"""
        return STRIPE_AVAILABLE and bool(STRIPE_SECRET_KEY)

    @staticmethod
    def create_checkout_session(user_id: int, email: str,
                                plan_id: str, billing_cycle: str = "monthly",
                                success_url: str = None,
                                cancel_url: str = None) -> Optional[dict]:
        """
        创建 Stripe Checkout Session

        :param user_id: 用户ID
        :param email: 用户邮箱
        :param plan_id: 订阅计划 (orbit/moonshot)
        :param billing_cycle: 计费周期 (monthly/yearly)
        :param success_url: 支付成功后跳转 URL
        :param cancel_url: 取消支付后跳转 URL
        :return: {"session_id": str, "checkout_url": str} 或 None
        """
        if not StripeHandler.is_available():
            logger.error("[Stripe] Stripe 未配置")
            return None

        price_id = PLAN_PRICE_MAP.get(plan_id, {}).get(billing_cycle)
        if not price_id:
            logger.error(f"[Stripe] 未找到价格配置: plan={plan_id}, cycle={billing_cycle}")
            return None

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=email,
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                success_url=success_url or f"{APP_BASE_URL}/settings/subscription?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{APP_BASE_URL}/settings/subscription?payment=cancelled",
                metadata={
                    "user_id": str(user_id),
                    "plan_id": plan_id,
                    "billing_cycle": billing_cycle,
                },
                subscription_data={
                    "metadata": {
                        "user_id": str(user_id),
                        "plan_id": plan_id,
                    },
                },
            )

            logger.info(f"[Stripe] Checkout Session 创建成功: user_id={user_id}, "
                        f"plan={plan_id}, session_id={session.id}")

            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }

        except stripe.error.StripeError as e:
            logger.error(f"[Stripe] 创建 Checkout Session 失败: {e}")
            return None

    @staticmethod
    def create_customer_portal_session(customer_id: str,
                                       return_url: str = None) -> Optional[str]:
        """
        创建 Stripe 客户门户 Session（用于管理订阅/发票）

        :param customer_id: Stripe Customer ID
        :param return_url: 返回 URL
        :return: 门户 URL 或 None
        """
        if not StripeHandler.is_available():
            return None

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url or f"{APP_BASE_URL}/settings/subscription",
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"[Stripe] 创建客户门户失败: {e}")
            return None

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> Optional[object]:
        """
        验证并构造 Webhook 事件

        :param payload: 请求体原始字节
        :param sig_header: Stripe-Signature 头
        :return: Stripe Event 对象或 None
        """
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("[Stripe] STRIPE_WEBHOOK_SECRET 未配置")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError:
            logger.error("[Stripe] Webhook 签名验证失败")
            return None
        except Exception as e:
            logger.error(f"[Stripe] Webhook 事件构造失败: {e}")
            return None

    @staticmethod
    def handle_webhook_event(event) -> dict:
        """
        处理 Stripe Webhook 事件

        :param event: Stripe Event 对象
        :return: {"handled": bool, "action": str, "details": dict}
        """
        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"[Stripe] 收到 Webhook 事件: {event_type}")

        if event_type == "checkout.session.completed":
            return StripeHandler._handle_checkout_completed(data)

        elif event_type == "customer.subscription.updated":
            return StripeHandler._handle_subscription_updated(data)

        elif event_type == "customer.subscription.deleted":
            return StripeHandler._handle_subscription_deleted(data)

        elif event_type == "invoice.payment_succeeded":
            return StripeHandler._handle_payment_succeeded(data)

        elif event_type == "invoice.payment_failed":
            return StripeHandler._handle_payment_failed(data)

        else:
            logger.debug(f"[Stripe] 未处理的事件类型: {event_type}")
            return {"handled": False, "action": "ignored", "details": {}}

    @staticmethod
    def _handle_checkout_completed(session) -> dict:
        """处理 Checkout 完成事件"""
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        billing_cycle = metadata.get("billing_cycle", "monthly")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if user_id and plan_id:
            try:
                from monetization.subscription import SubscriptionManager
                # 更新订阅状态
                success, msg = SubscriptionManager.upgrade_subscription(
                    int(user_id), plan_id, billing_cycle
                )
                # 保存 Stripe Customer ID 和 Subscription ID
                if success:
                    SubscriptionManager.save_stripe_info(
                        int(user_id), customer_id, subscription_id
                    )
                logger.info(f"[Stripe] Checkout 完成: user_id={user_id}, "
                            f"plan={plan_id}, success={success}")
                return {
                    "handled": True,
                    "action": "subscription_activated",
                    "details": {
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "customer_id": customer_id,
                    },
                }
            except Exception as e:
                logger.error(f"[Stripe] 处理 Checkout 完成失败: {e}")

        return {"handled": False, "action": "checkout_completed_failed", "details": {}}

    @staticmethod
    def _handle_subscription_updated(subscription) -> dict:
        """处理订阅更新事件"""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")
        status = subscription.get("status")

        logger.info(f"[Stripe] 订阅更新: user_id={user_id}, status={status}")

        if user_id and status == "canceled":
            try:
                from monetization.subscription import SubscriptionManager
                SubscriptionManager.cancel_subscription(int(user_id))
            except Exception as e:
                logger.error(f"[Stripe] 处理订阅取消失败: {e}")

        return {
            "handled": True,
            "action": "subscription_updated",
            "details": {"user_id": user_id, "status": status},
        }

    @staticmethod
    def _handle_subscription_deleted(subscription) -> dict:
        """处理订阅删除事件（到期/取消）"""
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")

        if user_id:
            try:
                from monetization.subscription import SubscriptionManager
                # 降级为 Free
                SubscriptionManager.upgrade_subscription(int(user_id), "free", "monthly")
                logger.info(f"[Stripe] 订阅已删除，降级为 Free: user_id={user_id}")
            except Exception as e:
                logger.error(f"[Stripe] 处理订阅删除失败: {e}")

        return {
            "handled": True,
            "action": "subscription_deleted",
            "details": {"user_id": user_id},
        }

    @staticmethod
    def _handle_payment_succeeded(invoice) -> dict:
        """处理支付成功事件（续费成功）"""
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")
        amount_paid = invoice.get("amount_paid", 0)

        logger.info(f"[Stripe] 支付成功: customer={customer_id}, "
                    f"amount={amount_paid/100:.2f}")

        return {
            "handled": True,
            "action": "payment_succeeded",
            "details": {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "amount": amount_paid,
            },
        }

    @staticmethod
    def _handle_payment_failed(invoice) -> dict:
        """处理支付失败事件"""
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")

        logger.warning(f"[Stripe] 支付失败: customer={customer_id}")

        # TODO: 发送支付失败通知邮件

        return {
            "handled": True,
            "action": "payment_failed",
            "details": {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
            },
        }
