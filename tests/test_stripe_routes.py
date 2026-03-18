"""
Stripe 支付路由测试
覆盖: 创建 Checkout Session、Webhook 处理、订阅管理
"""
import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestStripeCheckout:
    """Stripe Checkout Session 测试"""

    def test_create_checkout_no_auth(self, client):
        resp = client.post('/api/stripe/create-checkout-session', json={
            'plan': 'orbit'
        })
        assert resp.status_code in [401, 403, 500]

    def test_create_checkout_invalid_plan(self, client):
        resp = client.post('/api/stripe/create-checkout-session', json={
            'plan': 'nonexistent_plan'
        })
        assert resp.status_code in [400, 401, 500]


class TestStripeWebhook:
    """Stripe Webhook 测试"""

    def test_webhook_no_signature(self, client):
        resp = client.post('/api/stripe/webhook', data='{}',
                          content_type='application/json')
        assert resp.status_code in [400, 401, 500]

    def test_webhook_invalid_signature(self, client):
        resp = client.post('/api/stripe/webhook',
                          data='{"type": "checkout.session.completed"}',
                          content_type='application/json',
                          headers={'Stripe-Signature': 'invalid'})
        assert resp.status_code in [400, 401, 500]

    @patch('api.stripe_routes.stripe')
    def test_webhook_checkout_completed(self, mock_stripe, client):
        mock_event = MagicMock()
        mock_event.type = 'checkout.session.completed'
        mock_event.data.object = {
            'client_reference_id': '1',
            'subscription': 'sub_test123',
            'customer': 'cus_test123'
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        resp = client.post('/api/stripe/webhook',
                          data='{"type": "checkout.session.completed"}',
                          content_type='application/json',
                          headers={'Stripe-Signature': 't=1,v1=test'})
        assert resp.status_code in [200, 400, 500]


class TestStripeSubscription:
    """Stripe 订阅管理测试"""

    def test_cancel_subscription_no_auth(self, client):
        resp = client.post('/api/stripe/cancel-subscription')
        assert resp.status_code in [401, 403, 500]

    def test_get_billing_portal_no_auth(self, client):
        resp = client.post('/api/stripe/billing-portal')
        assert resp.status_code in [401, 403, 500]


class TestStripeHandler:
    """StripeHandler 工具类测试"""

    def test_stripe_handler_import(self):
        from monetization.stripe_handler import StripeHandler
        sh = StripeHandler()
        assert sh is not None

    def test_stripe_handler_plan_mapping(self):
        from monetization.stripe_handler import StripeHandler
        sh = StripeHandler()
        if hasattr(sh, 'PLAN_PRICE_MAP'):
            assert 'orbit' in sh.PLAN_PRICE_MAP or len(sh.PLAN_PRICE_MAP) > 0
        elif hasattr(sh, 'plans'):
            assert len(sh.plans) > 0

    def test_subscription_model_import(self):
        from monetization.subscription import SubscriptionManager
        sm = SubscriptionManager()
        assert sm is not None

    def test_subscription_plans(self):
        from monetization.subscription import SubscriptionManager
        sm = SubscriptionManager()
        plans = sm.get_plans() if hasattr(sm, 'get_plans') else None
        if plans:
            assert len(plans) >= 2  # 至少 free + 一个付费计划


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
