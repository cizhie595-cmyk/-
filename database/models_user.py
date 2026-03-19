"""
用户系统模型层
包含: UserModel, UserOAuthModel
对应表: users, user_oauth
"""

import json
from datetime import datetime
from typing import Optional
from database.connection import db


class UserModel:
    """用户模型 - 对应 users 表"""

    @staticmethod
    def create(username: str, email: str, password_hash: str, **kwargs) -> int:
        """创建新用户，返回用户 ID"""
        data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
        }
        data.update(kwargs)
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO users ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def get_by_id(user_id: int) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))

    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))

    @staticmethod
    def get_by_username(username: str) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM users WHERE username = %s", (username,))

    @staticmethod
    def update(user_id: int, data: dict) -> int:
        """更新用户信息，返回受影响行数"""
        if not data:
            return 0
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE users SET {set_clause} WHERE id = %s"
        return db.execute(sql, (*data.values(), user_id))

    @staticmethod
    def update_login(user_id: int):
        """更新最后登录时间和登录次数"""
        sql = "UPDATE users SET last_login_at = NOW(), login_count = login_count + 1 WHERE id = %s"
        db.execute(sql, (user_id,))

    @staticmethod
    def update_subscription(user_id: int, plan: str, billing_cycle: str = "monthly",
                            expires_at: datetime = None):
        """更新订阅信息"""
        sql = """UPDATE users SET subscription_plan = %s, billing_cycle = %s,
                 subscription_started_at = NOW(), subscription_expires_at = %s WHERE id = %s"""
        db.execute(sql, (plan, billing_cycle, expires_at, user_id))

    @staticmethod
    def update_ai_settings(user_id: int, settings: dict):
        """更新 AI 模型配置"""
        sql = "UPDATE users SET ai_settings = %s WHERE id = %s"
        db.execute(sql, (json.dumps(settings), user_id))

    @staticmethod
    def update_api_keys(user_id: int, encrypted_keys: str):
        """更新加密的 API 密钥配置"""
        sql = "UPDATE users SET api_keys_settings = %s WHERE id = %s"
        db.execute(sql, (encrypted_keys, user_id))

    @staticmethod
    def verify_email(user_id: int):
        """标记邮箱已验证"""
        sql = "UPDATE users SET is_verified = 1 WHERE id = %s"
        db.execute(sql, (user_id,))

    @staticmethod
    def deactivate(user_id: int):
        """停用账户"""
        sql = "UPDATE users SET is_active = 0 WHERE id = %s"
        db.execute(sql, (user_id,))

    @staticmethod
    def get_all(page: int = 1, per_page: int = 20) -> list[dict]:
        """分页获取所有用户"""
        offset = (page - 1) * per_page
        sql = "SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return db.fetch_all(sql, (per_page, offset))

    @staticmethod
    def count() -> int:
        """获取用户总数"""
        result = db.fetch_one("SELECT COUNT(*) AS cnt FROM users")
        return result["cnt"] if result else 0

    @staticmethod
    def search(query: str) -> list[dict]:
        """按用户名或邮箱搜索"""
        like = f"%{query}%"
        sql = "SELECT * FROM users WHERE username LIKE %s OR email LIKE %s ORDER BY created_at DESC"
        return db.fetch_all(sql, (like, like))


class UserOAuthModel:
    """OAuth 第三方登录模型 - 对应 user_oauth 表"""

    @staticmethod
    def create(user_id: int, provider: str, provider_uid: str, **kwargs) -> int:
        data = {
            "user_id": user_id,
            "provider": provider,
            "provider_uid": provider_uid,
        }
        data.update(kwargs)
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO user_oauth ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def get_by_provider(provider: str, provider_uid: str) -> Optional[dict]:
        sql = "SELECT * FROM user_oauth WHERE provider = %s AND provider_uid = %s"
        return db.fetch_one(sql, (provider, provider_uid))

    @staticmethod
    def get_by_user(user_id: int) -> list[dict]:
        return db.fetch_all("SELECT * FROM user_oauth WHERE user_id = %s", (user_id,))

    @staticmethod
    def update_tokens(oauth_id: int, access_token: str, refresh_token: str = None):
        sql = "UPDATE user_oauth SET access_token = %s, refresh_token = %s WHERE id = %s"
        db.execute(sql, (access_token, refresh_token, oauth_id))

    @staticmethod
    def delete(oauth_id: int):
        db.execute("DELETE FROM user_oauth WHERE id = %s", (oauth_id,))
