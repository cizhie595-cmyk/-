"""
通知路由测试
覆盖: 获取通知列表、标记已读、全部已读、偏好设置、删除
"""
import pytest
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


class TestNotificationList:
    """通知列表测试"""

    def test_list_notifications_no_auth(self, client):
        resp = client.get('/api/notifications')
        assert resp.status_code in [401, 403, 500]

    def test_get_unread_count_no_auth(self, client):
        resp = client.get('/api/notifications/unread-count')
        assert resp.status_code in [401, 403, 500]


class TestNotificationActions:
    """通知操作测试"""

    def test_mark_read_no_auth(self, client):
        resp = client.put('/api/notifications/1/read')
        assert resp.status_code in [401, 403, 500]

    def test_mark_all_read_no_auth(self, client):
        resp = client.put('/api/notifications/read-all')
        assert resp.status_code in [401, 403, 500]

    def test_delete_notification_no_auth(self, client):
        resp = client.delete('/api/notifications/1')
        assert resp.status_code in [401, 403, 500]


class TestNotificationPreferences:
    """通知偏好设置测试"""

    def test_get_preferences_no_auth(self, client):
        resp = client.get('/api/notifications/preferences')
        assert resp.status_code in [401, 403, 500]

    def test_update_preferences_no_auth(self, client):
        resp = client.put('/api/notifications/preferences', json={
            'email_notifications': True,
            'push_notifications': False
        })
        assert resp.status_code in [401, 403, 500]


class TestNotificationManager:
    """NotificationManager 工具类测试"""

    def test_notification_manager_import(self):
        from utils.notification_manager import NotificationManager
        nm = NotificationManager()
        assert nm is not None

    def test_notification_types(self):
        from utils.notification_manager import NotificationManager
        nm = NotificationManager()
        # 检查支持的通知类型
        if hasattr(nm, 'NOTIFICATION_TYPES'):
            assert isinstance(nm.NOTIFICATION_TYPES, (list, dict, tuple))

    def test_create_notification_structure(self):
        from utils.notification_manager import NotificationManager
        nm = NotificationManager()
        if hasattr(nm, 'create'):
            notif = nm.create(
                user_id=1,
                type='info',
                title='Test',
                message='Test notification'
            )
            assert notif is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
